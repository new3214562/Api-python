import nextcord
import json
import os
import requests
from nextcord.ext import commands
from nextcord.ui import Button, View, Modal, TextInput

# ตั้งค่า Bot และ Intents
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# ตั้งค่าไฟล์ JSON
DATA_FILE = "data.json"

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

# ตั้งค่าช่องแจ้งเตือน
ID_CH = 1342856050172493926

class AddRoleModal(Modal):
    def __init__(self):
        super().__init__(title="เพิ่ม Role ที่ขาย")
        self.role_id = TextInput(label="ID Role", placeholder="กรอก ID ของ Role", required=True)
        self.role_name = TextInput(label="ชื่อยศ", placeholder="กรอกชื่อยศที่จะขาย", required=True)
        self.price = TextInput(label="ราคา", placeholder="ระบุราคาเป็นพ้อยท์", required=True)

        self.add_item(self.role_id)
        self.add_item(self.role_name)
        self.add_item(self.price)

    async def callback(self, interaction: nextcord.Interaction):
        try:
            role_id = self.role_id.value.strip()
            role_name = self.role_name.value.strip()
            price = int(self.price.value.strip())

            role = interaction.guild.get_role(int(role_id))
            if not role:
                await interaction.response.send_message("❌ ไม่พบ Role นี้!", ephemeral=True)
                return

            data["roles"][role_id] = {
                "name": role_name,
                "price": price
            }
            save_data(data)

            await interaction.response.send_message(f"✅ เพิ่ม Role `{role_name}` ราคา `{price}` พ้อยท์แล้ว!", ephemeral=True)

        except ValueError:
            await interaction.response.send_message("❌ ราคาต้องเป็นตัวเลขเท่านั้น!", ephemeral=True)
        except Exception as e:
            print(f"Error in AddRoleModal: {e}")
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)
            
class AddRoleButton(Button):
    def __init__(self):
        super().__init__(label="เพิ่ม Role", style=nextcord.ButtonStyle.green, custom_id="add_role_button")

    async def callback(self, interaction: nextcord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ คุณไม่มีสิทธิ์เพิ่ม Role!", ephemeral=True)
            return

        await interaction.response.send_modal(AddRoleModal())

class BuyRoleModal(Modal):
    def __init__(self):
        super().__init__(title="ซื้อ Role")
        self.role_name = TextInput(label="ชื่อยศ", placeholder="กรอกชื่อยศที่ต้องการซื้อ", required=True)
        self.add_item(self.role_name)

    async def callback(self, interaction: nextcord.Interaction):
        try:
            role_name = self.role_name.value.strip()
            user_id = str(interaction.user.id)

            if user_id not in data["users"]:
                data["users"][user_id] = {"points": 0}

            # หา role_id จากชื่อยศที่กรอกมา
            role_id = None
            for rid, info in data["roles"].items():
                if info["name"] == role_name:
                    role_id = rid
                    break

            if role_id is None:
                await interaction.response.send_message("❌ ไม่พบ Role นี้ในรายการ!", ephemeral=True)
                return

            role = interaction.guild.get_role(int(role_id))
            if not role:
                await interaction.response.send_message("❌ Role นี้ถูกลบไปแล้ว!", ephemeral=True)
                return

            price = data["roles"][role_id]["price"]
            if data["users"][user_id]["points"] < price:
                await interaction.response.send_message(f"❌ พ้อยท์ไม่พอ! ต้องการ `{price}` พ้อยท์", ephemeral=True)
                return

            await interaction.user.add_roles(role)
            data["users"][user_id]["points"] -= price
            save_data(data)

            await interaction.response.send_message(f"✅ ซื้อ Role `{role.name}` สำเร็จ!", ephemeral=True)

            if notify_channel:
                await notify_channel.send(f"{interaction.user.mention} ซื้อ Role `{role.name}` ราคา `{price}` พ้อยท์!")

        except Exception as e:
            print(f"Error in BuyRoleModal: {e}")
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)
            
class BuyRoleButton(Button):
    def __init__(self):
        super().__init__(label="ซื้อ Role", style=nextcord.ButtonStyle.blurple, custom_id="buy_role_button")

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.response.send_modal(BuyRoleModal())

# ✅ ปุ่มเติมพอยท์
class TopUpButton(Button):
    def __init__(self):
        super().__init__(label="เติมพอยท์", style=nextcord.ButtonStyle.primary, custom_id="top_up_button")

    async def callback(self, interaction: nextcord.Interaction):
        modal = Modal(title="เติมพอยท์")
        modal.add_item(TextInput(label="ลิงก์ Gift", placeholder="วางลิงก์จาก TrueMoney Wallet"))

        async def modal_callback(inner_interaction: nextcord.Interaction):
            try:
                phone = "0802672257"
                gift_link = modal.children[0].value

                response = requests.post(
                    f"https://gift.truemoney.com/campaign/vouchers/{gift_link}/redeem",
                    data={"mobile": phone}
                )
                result = response.json()

                if result.get("status") == "SUCCESS" and result.get("amount") is not None:
                    amount = result["amount"]
                    user_id = str(inner_interaction.user.id)

                    if user_id not in data["users"]:
                        data["users"][user_id] = {"points": 0}

                    data["users"][user_id]["points"] += amount
                    save_data(data)

                    await inner_interaction.response.send_message(f"✅ เติมพอยท์สำเร็จ! ได้รับ `{amount}` พ้อยท์", ephemeral=True)
                else:
                    await inner_interaction.response.send_message("❌ เติมเงินไม่สำเร็จ!", ephemeral=True)
            except Exception as e:
                await inner_interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

        modal.on_submit = modal_callback
        await interaction.response.send_modal(modal)

# ✅ ปุ่มดูพอยท์
class CheckPointsButton(Button):
    def __init__(self):
        super().__init__(label="ดูพอยท์", style=nextcord.ButtonStyle.secondary, custom_id="check_points_button")

    async def callback(self, interaction: nextcord.Interaction):
        user_id = str(interaction.user.id)

        if user_id not in data["users"]:
            data["users"][user_id] = {"points": 0}

        points = data["users"][user_id]["points"]
        await interaction.response.send_message(f"👤 คุณมี `{points}` พ้อยท์", ephemeral=True)

class ListRolesButton(Button):
    def __init__(self):
        super().__init__(label="รายการ Role ที่ขาย", style=nextcord.ButtonStyle.gray, custom_id="list_roles_button")

    async def callback(self, interaction: nextcord.Interaction):
        if "roles" not in data:
            data["roles"] = {}

        if not data["roles"]:
            await interaction.response.send_message("❌ ไม่มี Role ที่ตั้งขายอยู่ในขณะนี้", ephemeral=True)
            return

        embed = nextcord.Embed(title="🛒 รายการ Role ที่ขาย", color=nextcord.Color.blue())

        for role_id, info in data["roles"].items():
            role = interaction.guild.get_role(int(role_id))
            if role is None:
                embed.add_field(name=f"❌ ไม่พบ Role ID: {role_id}", value=f"ราคา: {info['price']} พ้อยท์ (Role ถูกลบไปแล้ว)", inline=False)
            else:
                embed.add_field(name=info["name"], value=f"ราคา: {info['price']} พ้อยท์", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    global notify_channel
    notify_channel = bot.get_channel(ID_CH)
    if notify_channel:
        print(f"พบช่องแจ้งเตือน: {notify_channel.name}")
    else:
        print("❌ ไม่พบช่องแจ้งเตือน")

    print(f"บอทล็อกอินเป็น: {bot.user}")
    await bot.change_presence(activity=nextcord.Game(name="ขาย Role"))

@bot.command()
async def main(ctx: commands.Context):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้!")
        return

    view = View()
    view.add_item(AddRoleButton())
    view.add_item(BuyRoleButton())
    view.add_item(TopUpButton())
    view.add_item(CheckPointsButton())
    view.add_item(ListRolesButton())
    embed = nextcord.Embed(title='บอทขายยศ',description='กดปุ่มด้านล่างเพื่อใช้งาน',color=0xc3ed05)
    embed.set_image(url='https://cdn.discordapp.com/attachments/1172168380405526661/1176789842919702608/7cfef8409d92517cc9ab6a2ecf8730de.gif?ex=657025f2&is=655db0f2&hm=3f10e400b9d83a9284fff074beba8cb855ca09f2249a4614b5cc8057fd540a66&f=7f1e3f0b-ee9f-4e4e-a7a8-')

    await ctx.send(embed=embed, view=view)

bot.run(TOKEN)
