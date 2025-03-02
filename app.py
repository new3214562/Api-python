import nextcord
import json
import os
import requests
from nextcord.ext import commands
from nextcord.ui import Button, View, Modal, TextInput

intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "data.json"
LOG_CHANNEL_ID = 1342856050172493926  # ใส่ ID ช่อง log แจ้งเตือน

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"roles": {}, "users": {}}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

class AdminAddPointsModal(Modal):
    def __init__(self):
        super().__init__(title="เติมพ้อยท์ (Admin)")
        self.user_id = TextInput(label="ID ผู้ใช้", placeholder="กรอก ID ของผู้ใช้", required=True)
        self.points = TextInput(label="จำนวนพ้อยท์", placeholder="ระบุจำนวนพ้อยท์ที่ต้องการเพิ่ม", required=True)

        self.add_item(self.user_id)
        self.add_item(self.points)

    async def callback(self, interaction: nextcord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานปุ่มนี้!", ephemeral=True)
            return

        try:
            user_id = self.user_id.value.strip()
            points = int(self.points.value.strip())

            if user_id not in data["users"]:
                data["users"][user_id] = {"points": 0}

            data["users"][user_id]["points"] += points
            save_data(data)

            user = interaction.guild.get_member(int(user_id))
            if user:
                await user.send(f"✅ แอดมินได้เติมพ้อยท์ให้คุณจำนวน `{points}` พ้อยท์")
                
            await interaction.response.send_message(f"✅ เติมพ้อยท์ให้ <@{user_id}> จำนวน `{points}` พ้อยท์สำเร็จ!", ephemeral=True)

            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"**แอดมิน {interaction.user.mention} ได้เติมพ้อยท์ให้ <@{user_id}> จำนวน `{points}` พ้อยท์!**")

        except ValueError:
            await interaction.response.send_message("❌ กรุณากรอกจำนวนพ้อยท์เป็นตัวเลข!", ephemeral=True)
        except Exception as e:
            print(f"เกิดข้อผิดพลาด: {e}")  # เพิ่มการแสดงข้อผิดพลาดในคอนโซล
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)


class AdminAddPointsButton(Button):
    def __init__(self):
        super().__init__(label="เติมพ้อยท์ (Admin)", style=nextcord.ButtonStyle.danger, custom_id="admin_add_points_button")

    async def callback(self, interaction: nextcord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้ปุ่มนี้!", ephemeral=True)
            return

        await interaction.response.send_modal(AdminAddPointsModal())
        
class AddRoleModal(Modal):
    def __init__(self):
        super().__init__(title="เพิ่ม Role ที่ขาย")
        self.role_id = TextInput(label="ID Role", placeholder="กรอก ID ของ Role", required=True)
        self.name = TextInput(label="ชื่อยศ", placeholder="ชื่อยศที่จะขาย", required=True)
        self.price = TextInput(label="ราคา (พ้อยท์)", placeholder="ระบุราคา", required=True)

        self.add_item(self.role_id)
        self.add_item(self.name)
        self.add_item(self.price)

    async def callback(self, interaction: nextcord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ ไม่มีสิทธิ์", ephemeral=True)

        role_id, name, price = self.role_id.value, self.name.value, self.price.value

        try:
            price = int(price)
            role = interaction.guild.get_role(int(role_id))
            if not role:
                return await interaction.response.send_message("❌ ไม่พบ Role", ephemeral=True)

            data["roles"][role_id] = {"name": name, "price": price}
            save_data(data)

            await interaction.response.send_message(f"✅ เพิ่ม {name} เรียบร้อย!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ ผิดพลาด: {e}", ephemeral=True)

class AddRoleButton(Button):
    def __init__(self): super().__init__(label="เพิ่ม Role", style=nextcord.ButtonStyle.green)

    async def callback(self, interaction): await interaction.response.send_modal(AddRoleModal())

class ListRolesButton(Button):
    def __init__(self): super().__init__(label="รายการ Role", style=nextcord.ButtonStyle.gray)

    async def callback(self, interaction):
        embed = nextcord.Embed(title="รายการ Role ที่ขาย", color=0x3498db)
        for rid, info in data["roles"].items():
            embed.add_field(name=info["name"], value=f"ราคา: {info['price']} พ้อยท์", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class BuyRoleModal(Modal):
    def __init__(self): 
        super().__init__(title="ซื้อ Role")
        self.name = TextInput(label="ชื่อยศ", placeholder="ใส่ชื่อยศที่ต้องการซื้อ")
        self.add_item(self.name)

    async def callback(self, interaction):
        user_id = str(interaction.user.id)
        role_name = self.name.value.strip()
        role_id = next((rid for rid, info in data["roles"].items() if info["name"] == role_name), None)
        if not role_id:
            return await interaction.response.send_message("❌ ไม่พบยศนี้", ephemeral=True)

        role = interaction.guild.get_role(int(role_id))
        price = data["roles"][role_id]["price"]
        if data["users"].get(user_id, {"points": 0})["points"] < price:
            return await interaction.response.send_message(f"❌ พ้อยท์ไม่พอ ต้องการ {price} พ้อยท์", ephemeral=True)

        await interaction.user.add_roles(role)
        data["users"][user_id]["points"] -= price
        save_data(data)

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        await log_channel.send(f"✅ {interaction.user} ซื้อยศ {role.name} ราคา {price} พ้อยท์")

        await interaction.response.send_message(f"✅ ซื้อสำเร็จ!", ephemeral=True)

class BuyRoleButton(Button):
    def __init__(self): super().__init__(label="ซื้อ Role", style=nextcord.ButtonStyle.blurple)

    async def callback(self, interaction): await interaction.response.send_modal(BuyRoleModal())

class CheckPointsButton(Button):
    def __init__(self): super().__init__(label="ดูพ้อยท์", style=nextcord.ButtonStyle.secondary)

    async def callback(self, interaction):
        points = data["users"].get(str(interaction.user.id), {"points": 0})["points"]
        await interaction.response.send_message(f"คุณมี {points} พ้อยท์", ephemeral=True)

class TopUpModal(Modal):
    def __init__(self):
        super().__init__(title="เติมพ้อยท์")
        self.link = TextInput(label="ลิงก์ Gift", placeholder="วางลิงก์จาก TrueMoney Wallet")
        self.add_item(self.link)

    async def callback(self, interaction):
        phone = "0802672257"
        response = requests.post(f"https://gift.truemoney.com/campaign/vouchers/{self.link.value}/redeem", data={"mobile": phone}).json()

        if response.get("status") == "SUCCESS":
            amount = response["amount"]
            data["users"].setdefault(str(interaction.user.id), {"points": 0})["points"] += amount
            save_data(data)

            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            await log_channel.send(f"✅ {interaction.user} เติมเงินสำเร็จ {amount} พ้อยท์")

            await interaction.response.send_message(f"เติมพ้อยท์สำเร็จ ได้รับ {amount} พ้อยท์", ephemeral=True)
        else:
            await interaction.response.send_message("❌ เติมเงินไม่สำเร็จ", ephemeral=True)

class TopUpButton(Button):
    def __init__(self): super().__init__(label="เติมพ้อยท์", style=nextcord.ButtonStyle.primary)

    async def callback(self, interaction): await interaction.response.send_modal(TopUpModal())

@bot.command()
async def main(ctx):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้!")

    view = View()
    view.add_item(AdminAddPointsButton())
    view.add_item(AddRoleButton())
    view.add_item(BuyRoleButton())
    view.add_item(TopUpButton())
    view.add_item(CheckPointsButton())
    view.add_item(ListRolesButton())

    embed = nextcord.Embed(
        title="💎 ร้านขายยศ - ระบบพ้อยท์",
        description=(
            "🔹 **วิธีใช้งาน**\n"
            "➖ เติมพ้อยท์เพื่อซื้อยศในเซิร์ฟเวอร์\n"
            "➖ ตรวจสอบพ้อยท์คงเหลือของคุณ\n"
            "➖ ซื้อยศที่ต้องการด้วยพ้อยท์\n"
            "➖ แอดมินสามารถเติมพ้อยท์ให้ผู้ใช้ได้\n\n"
            "⚡ **ปุ่มเมนู**\n"
            "🔹 `เติมพ้อยท์` - เติมพ้อยท์เข้าสู่ระบบ\n"
            "🔹 `ดูพ้อยท์` - ตรวจสอบพ้อยท์ของคุณ\n"
            "🔹 `ซื้อ Role` - ซื้อยศที่คุณต้องการ\n"
            "🔹 `รายการ Role` - ดูรายการยศที่มีขาย\n"
        ),
        color=0x1abc9c
    )

    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1058504363036917920/1345465194775576596/Bael.png?ex=67c4a59b&is=67c3541b&hm=f1e88359c483cc1e13c54bd25a33b3f1997fab29dadf9b53f559e14584aee5a2&")  # ใส่ไอคอนร้านค้า
    embed.set_footer(text="📌 ระบบพัฒนาโดย ทีม Dev", icon_url="https://cdn-icons-png.flaticon.com/512/1828/1828640.png")  # ใส่เครดิต
    embed.set_author(name="ระบบร้านขายยศ", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)  # ใส่ไอคอนเซิร์ฟเวอร์

    await ctx.send(embed=embed, view=view)

@bot.event
async def on_ready():
    print(f"Bot {bot.user} พร้อมใช้งาน!")
    await bot.change_presence(activity=nextcord.Game("ขายยศ"))

bot.run("MTEzMDUyMTUwNjgxMjgwNTE5MA.GlwWBx.eDPahVoXKDvEqjwTkx4U-KvlKnrcC-_Hdkd6M0")
