import time , datetime , pytz , random , qrcode , io , asyncio , tempfile , csv
from io import BytesIO
import threading , os , shutil , glob , zipfile , string , requests , json , ssl
from telethon import TelegramClient, events, custom as ct, functions as fn, types as tp, helpers as hp
from telethon.errors import UserAlreadyParticipantError, UserNotParticipantError
from telethon.tl.types import InputChannel, InputChannelEmpty, InputChannelFromMessage
from telethon.errors import SessionPasswordNeededError, PasswordHashInvalidError, PhonePasswordFloodError, \
    AuthKeyDuplicatedError , PhoneNumberBannedError , FloodError
from telethon.errors.rpcerrorlist import (PeerFloodError, UserNotMutualContactError, UserPrivacyRestrictedError,
                                          UserChannelsTooMuchError, UserBotError, InputUserDeactivatedError,
                                          AuthKeyDuplicatedError, UsernameInvalidError, UserAlreadyParticipantError , FloodWaitError)
from telethon.sync import TelegramClient, functions, types, events, errors
from telethon import TelegramClient, events, Button
from telethon.tl.types import DocumentAttributeFilename
from pathlib import Path
from zipfile import ZipFile , BadZipFile
from asyncio import Semaphore
#from texts import *
from asyncio.exceptions import CancelledError
from pymongo import MongoClient , DESCENDING
import socks
import re

AGENTS_FILE = "agents.json"

# ======================= APIs =============================
api_id = 27879067
api_hash = "abec49863fe60689574a6b516e5ab55a"
bot_token = "8306504785:AAGTDylavFI0mvmrJsiG4BhpvI-WpOVFgaI"

owners = [1377923423, 124877150]

report_charge = 1377923423
clone_report = 1377923423
Restock_notification_channel = 1001874073158

agent_price = 500

report_group_check = 86400 #timestamp
support = 'GXS6666666'
usdt_address = "TGY3N2LKKfEXqjKaozF8u1TkCgSpKep2US"

headers = {
    'Content-Type': "application/json",
    'TRON-PRO-API-KEY': "20574170-defe-4030-bc58-6243b1e0a3fc"
}

semaphore = Semaphore(50)

# ======================= client ===========================
bot = TelegramClient('telebot', api_id, api_hash)
bot.start(bot_token=bot_token)

# DB connect (PyMonogo) ---------------------------------------
client = MongoClient("mongodb://dylee:dylee001129@localhost:27017/?authSource=admin")
main_db = "xiufujiqirenbot"
dbm = client[main_db]

users = dbm['users']
settings = dbm['settings']
products = dbm['products']
payments = dbm['payments']
items = dbm['items']
reports = dbm['reports']
sales = dbm["sales"]
uploads = dbm["uploads"]
block = dbm["block"]

#buttons --------------------------------------------------
ch_keyboard = [
    [Button.text("🧍‍♂️️用户中心", resize=True), Button.text("🔹购买记录", resize=True), Button.text("🛒商品列表", resize=True)],
    [ Button.text("💳充值余额", resize=True)],
    [Button.text("📱联系客服", resize=True), Button.text("🌐English", resize=True), Button.text("🤝商店克隆", resize=True)]
]

en_keyboard = [
    [Button.text("🧍‍♂️️User Center", resize=True), Button.text("🔹Buy history", resize=True), Button.text("🛒Product List", resize=True)],
    [Button.text("📱Contact Me", resize=True), Button.text("🌐中文语言", resize=True), Button.text("💳Recharge", resize=True)]
]

back_button = [[Button.text("🔙返回菜单", resize=True)]]
# reply texts ------------------------------------------------------

en_start = f"""<b>🏁Welcome to, Wish you prosperity

+xx quickly selects the appropriate product according to the number (for example, if you want to find a British number, you send: +44)

You can add me to your group and set me as the administrator, send /start within the group to quickly achieve account distribution, improve efficiency

</b>"""

ch_start = f"""<b>🏁欢迎光临，祝您发财

+xx   根据号段快速选择适配商品（举例 如果你想找英国号，那你就发送： +44 ）

您可以将我添加到您的群组并设置为管理员，在群组内发送 /start 快速实现账号分发

</b>"""

en_support = f"""☎️ Customer Service:@GXS6666666
☎️ Our Channel @GXS666666666
🌈Please make a small test purchase first to avoid unnecessary disputes! Thank you for your cooperation!!!"""

ch_support = f"""☎️ 客服: @GXS6666666
🔉 频道 @GXS666666666
🌈首次购买请少量测试 谢谢合作‼️
            """

# DB Setup -------------------------------------------------
if settings.count_documents({}) < 1:
    data = {"is_main": True, "base_time": None}
    settings.insert_one(data)

if reports.count_documents({}) < 1:
    reports.insert_one({"main": True , "last_check" : None})

# set place to item and product for ordering show list
# pros = list(products.find({}))
# for i in pros:
#     if i.get('place'):
#         pass
#     else:
#         products.update_one({"pid": i['pid']}, {"$set": {'place': 0}})

# ite = list(users.find({}))
# for i in ite:
#     if i.get('step') != None:
#         pass
#     else:
#         users.update_one({"userid": i['userid']}, {"$set": {'step': 'none'}})

def install_db():
    my_database = client[main_db]
    collections = ["users", "settings", "products", "payments", "items", "reports","sales" , "uploads" , "block"]  # "cryptomus"]
    for i in collections:
        sample_document = {"key": "value"}
        my_collection = my_database[i]
        my_collection.insert_one(sample_document)
        result = my_collection.delete_one(sample_document)

install_db()

#---- required folders
os.makedirs('sold', exist_ok=True)
os.makedirs('downloads', exist_ok=True)
##------------------------------------------------------
customers_token = []

def admins_profit(db_name):
    con = client[db_name]
    conf = con['configs']
    srch = conf.find_one({"main" : True})
    if srch.get("profit_rate"):
        return srch.get("profit_rate")
    else:
        return None

async def loop_news(**kwargs):
    cat = kwargs.get("cat")
    sub = kwargs.get("sub")
    count = kwargs.get("count")
    price = kwargs.get("price")
    final = kwargs.get("final")

    if not all([cat, sub, count, price, final]):
        print("empty cont")
        return

    for i in customers_token:
        prof = admins_profit(i["DB"])
        print(prof , price)
        if prof:
            cl = TelegramClient(session=f"admin_bots/{i['DB']}", api_id=3680948,
                                 api_hash='c34e4abd69b50710f4df2c1651c88029')
            try:
                nprice = prof + price # Adding profit to the price

                await cl.connect()  # Ensure connection

                await cl.start(bot_token=i['token'])
                buttons = [[Button.url("⭕ 自助提号", f"https://t.me/{i['DB']}"),
                            Button.url("📞 售后客服", f"https://t.me/{i['admin']}")]]

                message_text = f"""🟢🟢🟢库存更新🟢🟢🟢

🏪分类：{cat}
🛍商品：{sub}
🛒上传数量： {count} 个
💰单价： {round(nprice, 2)}U
🆕当前库存： {final} 个
                """

                await cl.send_message(i["upload_note"], message_text, buttons=buttons)

            except Exception as e:
                print("Error in note update:", e)

            finally:
                try:
                    await cl.disconnect()
                except Exception as e:
                    print("Error in bot disconnect:", e)

    return

def date_to_timestamp(date_str, format="%Y-%m-%d"):
    dt = datetime.datetime.strptime(date_str, format)
    return int(dt.timestamp())

async def collect_report(btime = None):
    # add base time for report (update per 24H)
    #re_data = reports.find_one({"main" : True})
    if btime:
        base_time = date_to_timestamp(btime)
    else:
        base_time = time.time() - 86400

    # if base_time and time.time() - base_time > 86400:
    #     new_time = base_time + 86400
    #     reports.update_one({"main" : True}, {"$set" : {"last_check" : new_time}})
    #     base_time = time.time()
    #
    # elif base_time == None:
    #     reports.update_one({"main": True}, {"$set": {"last_check": time.time()}})
    #     base_time = time.time()

    #get last 24 hours payments:
    pays = list(payments.find({}))
    total_pays = 0
    amounts = 0
    for i in pays:
        if i.get('paid_time') == None:
            continue
        try:
            ts = i['paid_time'] // 1000
        except Exception as e:
            continue
        total_pays += 1
        if ts >= base_time:
            amounts += i['amount']

    #total sales of 24hours  / bad accounts / profits /
    get_sales = list(sales.find({}))
    total_sales = 0 #total accounts that sold
    bad_accounts = 0
    profits = 0
    consumption = 0
    loss = 0
    more_sales = {}

    for s in get_sales:
        if s['time'] >= base_time:
            try:
                total_sales += s["total_accounts"]
                bad_accounts += s.get("bad_account") or 0
                profits += s.get("profit") or 0
                consumption += s["cost"]
                profit_base = s.get("profitbase") or 0
                main_price = s.get("price" , 0) - profit_base #without profit
                loss += main_price * s.get("bad_account") or 0
            except:
                continue

            if more_sales.get(s["cat"]):
                more_sales[s["cat"]] += s["total_accounts"]
            else:
                more_sales[s["cat"]] = s["total_accounts"]

    top_5 = sorted(more_sales.items(), key=lambda x: x[1], reverse=True)[:5]

    # total uploads in 24 hours
    # total uploads
    get_uploads = list(uploads.find({}))
    total_uploads = 0
    for i in get_uploads:
        if i["time"] >= base_time:
            total_uploads += i["counts"]

    # users balance and used balances
    get_users = list(users.find({}))
    total_balances = 0
    used_balanced = 0
    total_users_have_balance = 0
    for i in get_users:
        if i['userid'] == 5090865464:
            continue
        if i.get("balance", 0) > 0:
            total_users_have_balance += 1
        total_balances += i['balance']
        used_balanced += i["used_balance"]

    text = f"""<b>🗓日期|🕟时间：{china_time()}

🕔保存报告时间：{china_time(base_time)}

👥用户总数 : {len(get_users)}
🔸拥有余额的用户总数：{total_users_have_balance} 个
💴当前用户总余额：{round(total_balances, 3)} U
💸当日用户余额消耗总额(已购买)：{round(consumption, 3)} U
💰过去 24 小时内支付的总金额 : {round(amounts, 3)} U
💰🔢过去24小时付款总数 : {total_pays} 个
😭堵塞造成的损失：{round(loss, 3)} U
🍑今日盈利：{round(profits, 3)} U
🧨被冻结账户数量：{bad_accounts}个
🛒当日累积售出账户数量：{total_sales} 个
↖️当日总计上传账户：{total_uploads} 个
5️⃣前 5 名销售类别：<code>
{top_5}
<code>
</b>"""

    return text

async def auto_report():
    while True:
        try:
            get_report = await collect_report()
            await bot.send_message(entity=report_charge,
                                   message=get_report , parse_mode="html")
        except Exception as e:
            print(e)
            await bot.send_message(entity=report_charge,
                                   message=f"error in reporter {e}", parse_mode="html")

        await asyncio.sleep(86400)

def get_user(uid: int):
    res = users.find_one({"userid": uid})
    if res != None:
        return res
    else:
        return None

def set_step(uid , status):
    users.update_one({"userid" : uid} , {"$set" : {"step" : status}})

def get_files(path, all=False):
    if all == False:

        contents = os.listdir(path)

        session_files = [name for name in contents if
                         name.endswith('.session') and os.path.isfile(f"{path}/{name}")]

        text_files = [
            name for name in os.listdir(path)
            if name.endswith('.txt') and os.path.isfile(os.path.join(path, name))
        ]
        full = 0
        # خطوط هر فایل را بشمارید
        for text_file in text_files:
            file_path = os.path.join(path, text_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
                    line_count = len(lines)
                    full += line_count
            except Exception as e:
                print("error in countring file" , e)

        if session_files:
            # اگر فایل‌های .session وجود دارند، تعداد آنها را برگردانید
            return len(session_files)

        elif full > 0:
            return full

        else:
            # اگر فایل‌های .session وجود ندارند، تعداد فولدرها را برگردانید
            folders = [name for name in contents if os.path.isdir(f"{path}/{name}")]
            return len(folders)

        # folders = [name for name in contents if os.path.isdir(os.path.join(path, name))]

        # num_folders = len(folders)
        # return num_folders
    else:
        base_path = path

        try:
            contents = os.listdir(base_path)
        except FileNotFoundError:
            print(f"The directory {base_path} does not exist.")
            return 0

        folders = [name for name in contents if os.path.isdir(f"{base_path}/{name}")]

        full = 0

        for folder in folders:
            current_path = f"{base_path}/{folder}"
            # print(f"Current path: {current_path}")

            try:
                contents = os.listdir(current_path)
            except FileNotFoundError:
                print(f"The directory {current_path} does not exist.")
                continue

            session_files = [name for name in contents if
                             name.endswith('.session') and os.path.isfile(f"{current_path}/{name}")]

            text_files = [
                name for name in os.listdir(current_path)
                if name.endswith('.txt') and os.path.isfile(os.path.join(current_path, name))
            ]

            # خطوط هر فایل را بشمارید
            for text_file in text_files:
                file_path = os.path.join(current_path, text_file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        lines = file.readlines()
                        line_count = len(lines)
                        full += line_count
                except Exception as e:
                    print("error in lines", e)

            # print(f"Session files in {current_path}: {len(session_files)}")

            if session_files:
                full += len(session_files)
            else:
                subfolders = [name for name in contents if os.path.isdir(f"{current_path}/{name}")]
                full += len(subfolders)

        return full

        # folders = [name for name in contents if os.path.isdir(os.path.join(path, name))]
        #
        # num_folders = len(folders)
        # return num_folders

def generate_qr_file(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    # Save QR code to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp_file, 'PNG')
    temp_file.close()

    return temp_file.name

def id_generator(size=7, chars=string.ascii_lowercase):
    return str(''.join(random.choice(chars) for _ in range(size)))

def zip_file(path, format, zipname, count):
    if format == "session":
        session_files = glob.glob(os.path.join(path, '*.session'))
        json_files = glob.glob(os.path.join(path, '*.json'))

        selected_files = random.sample(session_files, count)
        selected_files += [file for file in json_files if
                           Path(file).stem in [Path(session).stem for session in selected_files]]

        with zipfile.ZipFile(f"sold/{zipname}", 'w') as zipf:
            for file in selected_files:
                zipf.write(file, os.path.basename(file))

        for i in selected_files:
            os.remove(i)

        return True

    if format == "txt":
        text_files = [
            name for name in os.listdir(path)
            if name.endswith('.txt') and os.path.isfile(os.path.join(path, name))
        ]
        texts = []
        # خطوط هر فایل را بشمارید

        for text_file in text_files:
            file_path = os.path.join(path, text_file)

            try:
                try:
                    # خواندن خطوط فایل اصلی
                    with open(file_path, 'r', encoding='utf-8') as file:
                        lines = file.readlines()

                    nb = 0
                    remaining_lines = []
                    for i, line in enumerate(lines):
                        if nb < count:
                            texts.append(line.strip())  # ذخیره خطوط انتخاب‌شده
                            nb += 1
                        else:
                            remaining_lines.append(line)  # ذخیره خطوط باقی‌مانده

                    # بازنویسی فایل اصلی بدون خطوط انتخاب‌شده
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.writelines(remaining_lines)

                except Exception as e:
                    print(f"error in procsing files {text_file}: {e}")
                    continue

                with open(f"sold/{zipname}.txt", 'w', encoding='utf-8') as file2:
                    to_add = "\n".join(texts)
                    file2.write(to_add)

                with zipfile.ZipFile(f"sold/{zipname}", 'w') as zipf:
                    zipf.write(f"sold/{zipname}.txt",f"{zipname}.txt")

                try:
                    os.remove(f"sold/{zipname}.txt")
                except Exception as e:
                    print(":error in remove file:" ,e)

                return True
            except Exception as e:
                print(e)

    elif format == "tdata":
        folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]

        # Select 10 random folders
        selected_folders = random.sample(folders, count)

        # Create a zip file and add the selected folders
        with zipfile.ZipFile(os.path.join('sold', zipname), 'w') as zipf:
            for folder in selected_folders:
                folder_path = os.path.join(path, folder)
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, path))

        # Delete the selected folders
        for folder in selected_folders:
            folder_path = os.path.join(path, folder)
            for root, dirs, files in os.walk(folder_path, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(folder_path)
        return True

def check_files(path):
    contents = os.listdir(path)

    session_files = [name for name in contents if
                     name.endswith('.session') and os.path.isfile(os.path.join(path, name))]

    text_files = [
        name for name in os.listdir(path)
        if name.endswith('.txt') and os.path.isfile(os.path.join(path, name))
    ]
    full = 0
    # خطوط هر فایل را بشمارید
    for text_file in text_files:
        file_path = os.path.join(path, text_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                line_count = len(lines)
                full += line_count
        except Exception as e:
            pass

    if session_files:
        # اگر فایل‌های .session وجود دارند، تعداد آنها را برگردانید
        return {"session": len(session_files)}

    elif full > 0:
        return {"txt": full}

    else:
        # اگر فایل‌های .session وجود ندارند، تعداد فولدرها را برگردانید
        folders = [name for name in contents if os.path.isdir(os.path.join(path, name))]
        return {"tdata": len(folders)}

def random_api():
    with open('api.csv') as file:
        csvreader = csv.reader(file)
        rows = []
        for row in csvreader:
            rows.append(row)
        random_get = random.choice(rows)
    return random_get

def china_time(timestamp  = None):
    if timestamp == None:
        timestamp = round(time.time())
    # Convert the timestamp to a datetime object in UTC
    dt_utc = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)

    # Define China Standard Time (CST) time zone
    cst = pytz.timezone('Asia/Shanghai')

    # Convert the UTC datetime object to CST
    dt_cst = dt_utc.astimezone(cst)

    # Format the datetime object to a string
    chinese_date_time = dt_cst.strftime("%Y-%m-%d %H:%M:%S")

    return chinese_date_time

def create_directory(path):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        os.makedirs(path, exist_ok=True)
        print(f"Directory '{path}' created successfully.")
        return True
    except OSError as error:
        return False

def rename_directory(old_path, new_path):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        os.rename(old_path, new_path)
        print(f"Directory renamed from '{old_path}' to '{new_path}' successfully.")
        return True
    except OSError as error:
        print(f"Error renaming directory: {error}")
        return False

def update_products_counts():
    while True:

        try:
            # بروزرسانی تعداد کل محصولات در هر دسته
            pros = list(products.find({}).sort("place", 1))

            for cat in pros:
                total_products = 0  # مقدار دهی مجدد برای هر دسته
                item_list = list(items.find({"from_pid": cat['pid']}).sort("place", 1))

                for item in item_list:
                    #try:
                    total = get_files(f"{cat['ch']}/{item['ch']}", all=False)

                    # except Exception as e:
                    #     print("error in count pdate" , e)
                    #     items.update_one({"tid": item["tid"]}, {"$set": {"quan": 0}})
                    #     continue

                    if total is None:
                        continue

                    items.update_one({"tid": item["tid"]}, {"$set": {"quan": total}})
                    total_products += total  # جمع تعداد محصولات برای دسته فعلی

                # بروزرسانی مقدار محصولات دسته فعلی در دیتابیس
                products.update_one({"pid": cat["pid"]}, {"$set": {"quan": total_products}})

        except Exception as e:
            print("error in update quan" , e)

        time.sleep(1)

async def check_input_usdt():
    print("checker is on ", china_time(time.time()))
    while True:
        await asyncio.sleep(6)
        base_time = settings.find_one({"is_main": True})
        base_time = base_time["base_time"]

        if base_time == None:
            base_time = round(time.time()) * 1000

        try:

            url = requests.get(
                f"https://api.trongrid.io/v1/accounts/{usdt_address}/transactions/trc20?limit=100&contract_address=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t&min_timestamp={base_time}&only_confirmed=true",
                headers=headers)

        except Exception as e:
            print("pay check error:", e)
            await asyncio.sleep(5)
            continue
        if url.status_code == 200 and len(url.json()['data']) > 0:
            for i in url.json()['data']:
                if i['to'] == usdt_address:
                    pass
                else:
                    continue
                trc20_balance = float(i['value']) / 1000000
                try:
                    check = payments.find_one({"amount": trc20_balance , "status" : None})
                    if check != None:
                        try:

                            await bot.send_message(entity=check['userid'],
                                                           message=f"✅ {trc20_balance}USDT 的交易正在处理中")
                        except Exception as e:
                            print("error in send msg to user",e)
                            continue

                        a = payments.update_one({"userid": int(check['userid']), "amount": float(trc20_balance) , "status" : None},
                                            {"$set": {"status": 2, "paid_time": i["block_timestamp"],
                                                      'tx_hash': i['transaction_id']}})

                        # add balance
                        search = users.find_one({"userid": int(check["userid"])})

                        old_usdt = round(search["balance"], 4)
                        new_usdt = old_usdt + round(trc20_balance,3)
                        users.update_one({"userid": int(check["userid"])}, {"$set": {"balance": new_usdt}})

                        text = f"""✅您的账户已增加 {trc20_balance}U"""

                        try:

                            await bot.send_message(entity=int(check["userid"]),
                                                           message=text)
                        except Exception as e:
                            print("line 655 eorr" ,e)

                        try:
                            await bot.send_message(entity=report_charge,
                                                           message=f"""💰收到了一份 充值订单 👏
🗓日期|时间：  {china_time()}
❤️来自用户：<a href="tg://user?id={int(check["userid"])}">{int(check["userid"])}</a>
💰充值金额：<code>{trc20_balance}U</code>
🟢当前余额：{new_usdt}U
➕哈希：<code>{i['transaction_id']}</code>
                        """, parse_mode='html')

                        except Exception as e:
                            print("error msg:", e)

                except Exception as e:
                    print("error in payment checker" , e)
                    continue

    settings.update_one({"is_main": True}, {"$set": {"base_time": round(time.time() - 700) * 1000}})

async def expire_check():
    print("exp checker is online")
    while True:
        await asyncio.sleep(3)

        check = list(payments.find({"status": None}))
        if len(check) > 0:
            for i in check:
                if i.get('expire') != None and (round(time.time()) - i['expire']) > 0: # 修改为 1200 并且添加 round()
                    payments.delete_one({'amount': i['amount']})
                    try:
                        await bot.send_message(entity=i['userid'], message="<b>❌ 订单支付超时(或金额错误)</b>",
                                                       parse_mode='html')
                    except Exception as e:
                        print("line 965 ",e)

sents = [0]

async def send_to_all(text , userid):
    "msgall"
    get_users = list(users.find({}))
    success = 0

    for i in get_users:
        try:
            await asyncio.sleep(0.04)
            await bot.send_message(entity=i['userid'], message=text, parse_mode='html')
            success += 1
            sents[0] += 1
        except:
            pass
    await bot.send_message(entity=userid, message=f"发送完成 | {success} SENT")
    sents[0] = 0
    return

clients = {}

tor = (socks.SOCKS5, f'127.0.0.1', 9050, True, None, None)

async def get_client(api_id, api_hash, proxy, count):
    if count not in clients:
        clients[count] = TelegramClient(f"logs/{count}.session", api_id=int(api_id), api_hash=api_hash, proxy=tor, timeout=7)
        await clients[count].connect()
    return clients[count]

async def collect_numbers(number , count):
    await asyncio.sleep(0.001)
    async with semaphore:
        await asyncio.sleep(0)

        api_id, api_hash = random_api()

        client = await get_client(api_id, api_hash, tor, count)

        await asyncio.sleep(0)

        try:
            await client.send_code_request(phone=number)
            await asyncio.sleep(0.01)
            return {"number": number, "status": "ACTIVE", "good": 1, "ban": 0, "error": 0}
        except PhoneNumberBannedError:
            return {"number": number, "status": "BAN", "good": 0, "ban": 1, "error": 0}
        except FloodWaitError as e:
            return {"number": number, "status": "ACTIVE", "good": 1, "ban": 0, "error": 0}
        except CancelledError as e:
            return {"number": number, "status": "ERROR", "good": 0, "ban": 0, "error": 1}
        except Exception as e:
            print(f"Error: {e}")
            return {"number": number, "status": "ERROR", "good": 0, "ban": 0, "error": 1}
        finally:
            try:
                clients.pop(count)
                await client.disconnect()
            except:
                pass

async def check_numbers(code = None , message_id = None):
    print("check numbers called")

    data = sales.find_one({"code": code})

    if data == None:
        return None

    all_sessions_state = []

    data_path = data["path"]
    file_type = data["type"]
    chat_id = data["user"]
    price = data["price"]

    account_names = []
    verified_names = []

    try:
        with ZipFile(f"sold/{data_path}", 'r') as zip_ref:
            all_items = zip_ref.namelist()

            #仅提取顶级文件夹（无嵌套文件夹）
            account_names.extend(item.split('/')[0] for item in all_items if '/' in item)

            # 仅提取顶级文件夹（无嵌套文件夹）
            account_names.extend(set(item.replace('.session', '') for item in all_items if item.endswith('.session') and '/' not in item))

            #return list(top_folders), session_files

    except BadZipFile:
        print("The ZIP file is corrupted or invalid." , data_path)
        return None
    if len(account_names) < 1:
        return None

    for n in account_names:
        if not str(n).startswith("+"):
            number = f"+{n}"
        else:
            number = n
        if number not in verified_names:
            verified_names.append(number)

    print(account_names)
    print(verified_names)

    count = 1

    for n in verified_names:
        try:
            all_sessions_state.append(asyncio.create_task(collect_numbers(n, count)))
            count += 1
            await asyncio.sleep(0)
        except Exception as e:
            print(e)
            #print("error un vee", e)

    data = await asyncio.gather(*all_sessions_state, return_exceptions=True)
    await asyncio.sleep(0)

    banned_numbers = []
    print(data)
    data = list(filter(None, data))

    for i in data:
        await asyncio.sleep(0)
        try:
            if i.get("status") != None and i.get("status") == "BAN":
                banned_numbers.append(i['number'])
        except:
            pass

    #to back
    cal = len(banned_numbers) * price
    user_data = get_user(chat_id)

    user_balance = user_data['balance'] + cal
    used_balanced = user_data['used_balance'] - cal

    #back to user
    users.update_one({"userid" : chat_id} , {"$set" : {"balance" : user_balance, 'used_balance' : used_balanced}})

    aadi = len(verified_names) - len(banned_numbers)

    information = sales.find_one({"code": code})
    bad_accounts = len(banned_numbers)
    old_profit = information.get("profit")
    profitbase = information.get("profitbase")
    if old_profit and profitbase:
        new_profit = aadi * profitbase
        loss = (information["price"] - profitbase) * bad_accounts
        new_cost = information["cost"] - information["price"] * bad_accounts
        sales.update_one({"code" : code} , {"$set" : {"bad_account" : bad_accounts , "profit" : new_profit , "cost" : new_cost}})
    else:
        new_profit = "未输入"
        loss = "未输入"

    try:
        # await context.bot.send_message(chat_id=chat_id , text=f"{round(cal, 3)}U 因帐户损坏而退回您的帐户✅")
        await bot.send_message(entity=chat_id, message=f"""<b>🟢正常： {aadi}个
🔴封禁： {len(banned_numbers)}个  {round(cal, 3)}U已自动退回到您的账户余额
            </b>""", parse_mode='html')
    except Exception as e:
        print(e)

    try:
        await bot.send_message(entity=report_charge, message=f"""<b>🔸ID: {chat_id}
\n🟢正常： {aadi}个
🔴封禁： {len(banned_numbers)}个  {round(cal, 3)}U已自动退回到您的账户余额

😍利润： {new_profit} U
❗️❗️堵塞造成的损坏：{loss} U

                    </b>""", parse_mode='html')
    except:
        pass

    return

@bot.on(events.CallbackQuery())
async def callback(event):
    await asyncio.sleep(0.03)
    callback : str = event.data.decode('utf-8')
    user_id = event.sender_id

    user = get_user(user_id)

    is_ban = block.find_one({"userid": user_id})
    #print(is_ban)
    if is_ban != None:
        return

        #print(callback)

    if callback.startswith("usd"):
        user = get_user(user_id)
        data = int(callback[3:])

        while True:
            await asyncio.sleep(0.2)

            random_number = round(random.uniform(0.001, 0.099), 3)
            amount = data + random_number

            check = payments.find_one({"amount": amount})

            if check == None:
                now_time = round(time.time())
                expires_in = round(time.time()) + 1200

                payments.insert_one(
                    {"amount": amount, "userid": user_id, "expire": expires_in})

                break
            else:
                continue

        await event.delete()

        qr_address = generate_qr_file(usdt_address)
        if user['lang'] == 'zh':
            await asyncio.sleep(0.2)
            await event.client.send_message(
                event.chat_id,
                file=qr_address,
                message=f"""<b>支付金额：<code>{amount}</code> USDT
收款地址：<code>{usdt_address}</code>
❗️请一定按照金额后面小数点转账，否则未到账概不负责❗️

创建时间：{china_time(now_time)}
结束时间：{china_time(expires_in)}
请在20分钟内支付完成，否则订单失效</b>""",
                parse_mode='html'
            )
        else:
            await asyncio.sleep(0.2)
            await event.client.send_message(
                event.chat_id,
                file=qr_address,
                message=f"""<b>Actual payment amount: <code>{amount}</code> USDT
Receiving Address: <code>{usdt_address}</code>
❗️ Please make sure to transfer the exact amount including decimals, we will not be responsible for any discrepancies due to incorrect amounts ❗️

Creation Time: {china_time(now_time)}
End Time: {china_time(expires_in)}
Please complete the payment within 20 minutes, otherwise the order will expire
</b>
                            """,
                parse_mode='html'
            )
        return

    elif callback == "cancel" or callback == "cancel_pid" or callback == "close":
        try:
            await event.delete()
        except:
            pass
        set_step(user_id, "none")
        return

    elif callback == "custom":
        set_step(user_id , "custom_pay")
        await event.delete()
        cancel_button = [[Button.text("🔙返回菜单" , resize=True)]]

        if user['lang'] == 'zh':
            await event.respond("输入 1 到 10000 之间的所需值:",buttons = ch_keyboard)
        else:
            await event.respond("Enter the desired value between 1 and 10000:", buttons = en_keyboard)
        return

    elif callback.startswith("subpid"):
        pid = callback[6:]
        idems = list(items.find({"from_pid": pid}).sort("place", 1))

        idems = sorted(idems, key=lambda i: i.get('quan', 0), reverse=True)

        plist = []

        if user["lang"] == "zh":

            for i in idems:
                plist.append([Button.inline(f"{i['ch']}({i['quan']})", f'utem{i["tid"]}')])

            plist.append([Button.inline('❌关闭', f'close'),
                          Button.inline('返回↩', f'backpu')])

            reply = f"""<b>🛒选择你需要的商品：\n❗️没使用过本店商品的，请先少量购买测试，以免造成不必要的争执！谢谢合作</b>"""
            await event.edit(reply, buttons=plist, parse_mode="html")

        else:
            for i in idems:
                plist.append([Button.inline(f"{i['ch']}({i['quan']})", f'utem{i["tid"]}')])

            plist.append([Button.inline('❌close', f'close'),
                          Button.inline('Back↩', f'backpu')])

            reply = f"""<b>🛒 Choose the items you need:\n❗️ If you have not used our products before, please make a small test purchase first to avoid unnecessary disputes! Thank you for your cooperation</b>"""

            await event.edit(reply, buttons=plist, parse_mode="html")

        return

    elif callback == "instract":
        await event.reply(text=f"@{support}")
        return

    elif callback == "backpu":
        pros = list(products.find({}).sort("place", 1))

        clist = []

        if user["lang"] == "zh":

            for i in pros:
                clist.append([Button.inline(f"{i['ch']}({i['quan']})", f'subpid{i["pid"]}')])

            clist.append([Button.inline('❌关闭', f'close')])

            reply = f"""<b>🛒选择你需要的商品：\n❗️没使用过本店商品的，请先少量购买测试，以免造成不必要的争执！谢谢合作</b>"""
            await event.edit(reply, buttons=clist, parse_mode="html")

        else:
            for i in pros:
                clist.append([Button.inline(f"{i['ch']}({i['quan']})", f'subpid{i["pid"]}')])

            clist.append([Button.inline('❌close', f'close')])

            reply = f"""<b>🛒 Choose the items you need:\n❗️ If you have not used our products before, please make a small test purchase first to avoid unnecessary disputes! Thank you for your cooperation</b>"""

            await event.edit(reply, buttons=clist, parse_mode="html")

        return

    elif callback.startswith("utem"):
        tid = callback[4:]
        idems = items.find_one({"tid": tid})

        total = idems.get("quan") or 0

        if total <= 0:
            if user['lang'] == 'zh':
                await event.answer(f"❌暂无服务请联系客服添加@{support}", alert=True)
            else:
                await event.answer(f"❌no service available please contact customer service to add @{support}", alert=True)
            return

        if user['lang'] == 'zh':
            inline = [
                [Button.inline("✅购买", f"buy{tid}"), Button.url("直登教程", url="https://t.me/GXS666666666/2")],  # 这里替换成实际链接
                [Button.inline("💒主菜单", f"backpu"),
                 Button.inline("返回↩️", f"subpid{idems['from_pid']}")]]

            await event.edit(f"""<b>✅您正在购买:  {idems['ch']}

💰 价格： {idems['price']} USDT
🏢 库存： {total}
❗️ 未使用过的本店商品的，请先少量购买测试，以免造成不必要的争执！谢谢合作！</b>""",parse_mode = 'html' , buttons = inline)

        else:
            inline = [[Button.inline("✅Buy", f"buy{tid}"),
                       Button.url("Use tutorial", url="https://t.me/GXS666666666/2")],
                      [Button.inline("💒Main menu", f"backpu"),
                       Button.inline("Return↩️",f"subpid{idems['from_pid']}")]]

            await event.edit(f"""<b>✅ You are buying: {idems['en']}

💰 Price: {idems['price']} USDT
🏢 Stock: {total}
❗️ If you have not used our products before, please make a small test purchase first to avoid unnecessary disputes! Thank you for your cooperation!</b>""",
                                  parse_mode = 'html' , buttons = inline)

    elif callback.startswith("buy"):
        cuds = callback[3:]

        cancel_button = [[Button.text("🔙返回菜单", resize=True)]]

        if user['lang'] == "en":
            await event.reply(f"""Enter quantity:\nFormat: <code>Buy 10</code> Or <code>10</code>""",
                                           parse_mode='html', buttons=cancel_button)
        else:
            await event.reply(f"""请输入数量：格式：<code>购买 10</code> 或 <code>10</code>""",
                                           parse_mode='html' , buttons=cancel_button)

        set_step(user_id, f"buy{cuds}")
        return

    elif callback.startswith("acc_"):
        await asyncio.sleep(0.2)
        tid = callback.split("_")[1]
        count = callback.split("_")[2]
        count = int(count)
        utem = items.find_one({"tid": tid})
        uid = user_id

        if user['balance'] >= utem['price'] * count:
            dddd = products.find_one({"pid": utem['from_pid']})
            total: dict = check_files(f"{dddd['ch']}/{utem['ch']}")

            if total.get('session'):
                zname = f"{round(time.time())}_{uid}.zip"
                tryzip = zip_file(f"{dddd['ch']}/{utem['ch']}", 'session', zname, count)
                if tryzip:
                    new_balance = user['balance'] - utem['price'] * count
                    new_used = user["used_balance"] + utem['price'] * count
                    new_total = user['total_buy'] + count

                    users.update_one({"userid": uid},
                                     {"$set": {"balance": new_balance, "used_balance": new_used,
                                               'total_buy': new_total}})

                    id_order = id_generator()
                    profits = utem.get("profitof")
                    if profits:
                        profits = profits * count
                    else:
                        profits = None
                    data = {"user": uid, "total_accounts": count, "cat": f"{dddd['ch']}/{utem['ch']}",
                            "cost": utem['price'] * count, "price": utem['price'], "zname": zname, "time": time.time(),
                            "code": id_order, "path": zname, "type": "session" , "profit" : profits , "bad_account" : 0 , "profitbase" : utem.get("profitof")}
                    sales.insert_one(data)

                    try:
                        await bot.send_message(entity=report_charge, message=f"""🛒收到了一份 采购订单 🛍

🗓日期|时间：  {china_time()}
❤️来自用户：<a href="tg://user?id={uid}">{uid}</a>
🛍采购商品： {dddd['ch']}/{utem['ch']}
☑️采购数量：<code>{count}</code>
💰订单总额：{round(utem['price'] * count, 2)}
🟢当前余额：{round(new_balance, 3)} """, parse_mode='html')

                        await event.delete()

                    except:
                        pass

                    await asyncio.sleep(0.2)

                    if user['lang'] == "en":
                        await bot.send_message(entity=user_id,message="✅The purchase was made successfully")
                        await asyncio.sleep(0.1)
                        await event.client.send_file(user_id, f"sold/{zname}")
                        await bot.send_message("you back to main menu" , buttons=en_keyboard)

                        asyncio.create_task(check_numbers(id_order))

                    else:
                        await event.client.send_file(user_id, f"sold/{zname}")

                        asyncio.create_task(check_numbers(id_order))

                        await bot.send_message(entity=user_id,message="""✅您的账号正在打包！  欢迎再次光临❤️ 

‼️📁  直登号二级密码通常在账户文件内的“2FA.txt“或”TwoFA“或类型名字的 TXT文本中查看，协议号二级密码通常在账户的json文件内查看，若无以上文件或信息，密码咨询客服
‼️  同一份账户文件请勿在多个设备（包括云控）上打开使用，如直登号在电脑打开后又将账号上传云控或对账号文件进行其他转换/检测等操作。
‼️  利用第三方工具 机器人 对账户格式进行转换存在死号风险，请谨慎操作。请勿同时使用Session和Tdata，会造成抢登(LOG OUT)！请勿多设备登录  未配置IP大批量登录账号均存在风险
📁  如有问题 请在1小时内联系客服 手动售后流程：
        从机器人处转发购买的账户文件—在此处点击用户中心并将ID告知客服—截图您的购物情况 导出或截图您的首登问题
☎️售后客服：@GXS6666666
🟢补货通知群  @XXX""",parse_mode='html',buttons=ch_keyboard)
                        await asyncio.sleep(0.1)

                    set_step(user_id , "none")

                    return
                else:
                    await bot.send_message("稍后再试", buttons=ch_keyboard)
                    set_step(user_id, 'none')
                    return

            elif total.get("tdata"):
                zname = f"{round(time.time())}_{uid}.zip"

                tryzip = zip_file(f"{dddd['ch']}/{utem['ch']}", 'tdata', zname, count)
                if tryzip:
                    new_balance = user['balance'] - utem['price'] * count
                    new_used = user["used_balance"] + utem['price'] * count
                    new_total = user['total_buy'] + count

                    id_order = id_generator()

                    users.update_one({"userid": uid},
                                     {"$set": {"balance": new_balance, "used_balance": new_used,
                                               'total_buy': new_total}})

                    profits = utem.get("profitof")
                    if profits:
                        profits = profits * count
                    else:
                        profits = None

                    data = {"user": uid, "total_accounts": count, "zname": zname,
                            "cat": f"{dddd['ch']}/{utem['ch']}",
                            "cost": utem['price'] * count, "price": utem['price'], "time": time.time(),
                            "code": id_order, "path": zname, "type": "tdata", "profit" : profits , "bad_account" : 0, "profitbase" : utem.get("profitof")}
                    sales.insert_one(data)
                    try:
                        await event.delete()
                    except:
                        pass

                    try:
                        await bot.send_message(entity=report_charge, message=f"""🛒收到了一份 采购订单 🛍

🗓日期|时间：  {china_time()}
❤️来自用户：<a href="tg://user?id={uid}">{uid}</a>
🛍采购商品： {dddd['ch']}/{utem['ch']}
☑️采购数量：<code>{count}</code>
💰订单总额：{round(utem['price'] * count, 3)}
🟢当前余额：{round(new_balance, 3)} """, parse_mode='html')
                    except:
                        pass
                    await asyncio.sleep(0.2)

                    if user['lang'] == "en":

                        await bot.send_message(entity=user_id,message="✅The purchase was made successfully")
                        await bot.send_file(user_id, file=f"sold/{zname}",buttons=en_keyboard)
                        await asyncio.sleep(0.1)
                        asyncio.create_task(check_numbers(id_order))

                        set_step(user_id , 'none')
                        return

                    else:
                        await bot.send_message(entity=user_id, message="""✅您的账号正在打包！  欢迎再次光临❤️ 

‼️📁  直登号二级密码通常在账户文件内的“2FA.txt“或”TwoFA“或类型名字的 TXT文本中查看，协议号二级密码通常在账户的json文件内查看，若无以上文件或信息，密码咨询客服
‼️  同一份账户文件请勿在多个设备（包括云控）上打开使用，如直登号在电脑打开后又将账号上传云控或对账号文件进行其他转换/检测等操作。
‼️  利用第三方工具 机器人 对账户格式进行转换存在死号风险，请谨慎操作。请勿同时使用Session和Tdata，会造成抢登(LOG OUT)！请勿多设备登录  未配置IP大批量登录账号均存在风险
📁  如有问题 请在1小时内联系客服 手动售后流程：
        从机器人处转发购买的账户文件—在此处点击用户中心并将ID告知客服—截图您的购物情况 导出或截图您的首登问题
☎️售后客服：@GXS6666666
🟢补货通知群  @XXX""",parse_mode='html')
                        await bot.send_file(user_id, file=f"sold/{zname}", buttons=ch_keyboard)
                        await asyncio.sleep(0.1)
                        set_step(user_id, 'none')
                        asyncio.create_task(check_numbers(id_order))

                        return

                else:
                    await bot.send_message("稍后再试", buttons=ch_keyboard)
                    set_step(user_id, 'none')
                    return

            elif total.get('txt'):
                zname = f"{round(time.time())}_{uid}.zip"
                tryzip = zip_file(f"{dddd['ch']}/{utem['ch']}", 'txt', zname, count)
                if tryzip:
                    new_balance = user['balance'] - utem['price'] * count
                    new_used = user["used_balance"] + utem['price'] * count
                    new_total = user['total_buy'] + count
                    users.update_one({"userid": uid},
                                     {"$set": {"balance": new_balance, "used_balance": new_used,
                                               'total_buy': new_total}})
                    data = {"user": uid, "total_accounts": count, "cat": f"{dddd['ch']}/{utem['ch']}",
                            "cost": utem['price'] * count, "zname": zname, "time": time.time()}
                    sales.insert_one(data)

                    try:
                        await bot.send_message(entity=report_charge, message=f"""🛒收到了一份 采购订单 🛍

🗓日期|时间：  {china_time()}
❤️来自用户：<a href="tg://user?id={uid}">{uid}</a>
🛍采购商品： {dddd['ch']}/{utem['ch']}
☑️采购数量：<code>{count}</code>
💰订单总额：{round(utem['price'] * count, 3)}
🟢当前余额：{round(new_balance, 3)} """, parse_mode='html')
                    except:
                        pass

                    if user['lang'] == "en":
                        await asyncio.sleep(0.2)
                        await event.edit("✅The purchase was made successfully")
                        await bot.send_file(user_id, file=f"sold/{zname}", buttons=en_keyboard)

                    else:
                        await event.edit("""✅您的账号正在打包！  欢迎再次光临❤️ 

‼️📁  直登号二级密码通常在账户文件内的“2FA.txt“或”TwoFA“或类型名字的 TXT文本中查看，协议号二级密码通常在账户的json文件内查看，若无以上文件或信息，密码咨询客服
‼️  同一份账户文件请勿在多个设备（包括云控）上打开使用，如直登号在电脑打开后又将账号上传云控或对账号文件进行其他转换/检测等操作。
‼️  利用第三方工具 机器人 对账户格式进行转换存在死号风险，请谨慎操作。请勿同时使用Session和Tdata，会造成抢登(LOG OUT)！请勿多设备登录  未配置IP大批量登录账号均存在风险
📁  如有问题 请在1小时内联系客服 手动售后流程：
        从机器人处转发购买的账户文件—在此处点击用户中心并将ID告知客服—截图您的购物情况 导出或截图您的首登问题
☎️售后客服：@GXS6666666
🟢补货通知群  @XXX""")

                        await bot.send_file(user_id, file=f"sold/{zname}", buttons=ch_keyboard)

                    set_step(user_id , 'none')
                    return
                else:
                    await bot.send_message("稍后再试", buttons=ch_keyboard)
                    set_step(user_id, 'none')
                    return

        else:
            if user['lang'] == "en":

                await event.edit("try again later")

            else:
                await event.edit("稍后再试")

            set_step(user_id , 'none')
            return

    elif callback.startswith("active_"):
        main_data = callback.split("active_")[1]
        if main_data == "video":
            set_step(user_id, "none")
            active_clone = [[
                Button.inline("🤖创建机器人", "active_clone"),
                Button.inline("开始克隆", "active_token")]]

            await event.edit(f"""<b>加入分销系统 创建机器人的方法
1️⃣点击“创建机器人”前往@BotFather
2️⃣点击开始 start，点击或发送 /newbot - create a new bot   
3️⃣依次发送机器人的 <code>名字</code>（店铺名称）和机器人的 <code>@用户名</code>
4️⃣创建成功，复制 你得到的信息（包含api token）
点击观看演示视频： @hotgbots</b>""", buttons=active_clone, link_preview=False,
                                          parse_mode='html')

        elif main_data == "clone":
            set_step(user_id, "none")
            active_clone = [[Button.inline("📹 演示视频", "active_video"),
                             Button.inline("开始克隆", "active_token")]]

            await event.edit("从这部分构建你的机器人 @botfather", buttons = active_clone)

        elif main_data == "token":
            if user['balance'] >= agent_price:
                active_clone = [[Button.inline("📹 演示视频", "active_video"),
                                 Button.inline("🤖创建机器人", "active_clone"), ]]

                await event.edit(f"""请将包含机器人api token的信息转发到此处
复制下方格式替换冒号:后对应的值
api_token:机器人token
DB:机器人用户名
admin_id:管理ID
admin:管理员用户名
-----------------------------------------------------------
务必按照以上格式填写并发送""",
                                              buttons=active_clone , parse_mode = 'html')
                set_step(user_id , "agent")
                return
            else:
                await event.edit(f"<b>首先，将您的账户余额增加到+{agent_price}U</b>", parse_mode='html')
                set_step(user_id, "none")
                return

        return

    elif callback == "back_admin" and user_id in owners:

        message_text = (
            "欢迎使用机器人管理系统\n\n"
            "<b>🔍 搜索用户信息：</b> <code>/info UID</code>\n"
            "<b>💰 增加或减少用户余额：</b> <code>/bal UID +/-AMOUNT</code>\n"
            "   例如: <code>/bal 12343344 +40</code>\n"
            "<b>📊 报告所有用户：</b> <code>/users</code>\n"
        )

        await event.edit(message_text, parse_mode='html')

        return

    elif callback == "back" and user_id in owners:
        await event.delete()
        return

    elif callback == "addp" and user_id in owners:
        await event.edit(
            "输入产品类别中英文名称:\n例如：\n\n<code>🌍飞机编号✈印度尼西亚️tdata|🌍number✈Indonesiatdata</code>\n\n"
            "不要忘记名称以 | 开头。分离", buttons = back_button, parse_mode='html')

        set_step(user_id , "getsubname")

        return

    elif callback == "delp" and user_id in owners:
        plist = [
            [
                Button.inline('↩️关闭', 'back_admin')]
        ]

        pros = list(products.find().sort("place", 1))

        for i in pros:
            plist.append([Button.inline(i['ch'], f'rem{i["pid"]}')])

        await event.edit("选择其类别以将其删除:", buttons = plist)
        return

    elif callback == "renp" and user_id in owners:
        plist = [
            [
                Button.inline('↩️关闭', 'back_admin')]
        ]

        pros = list(products.find().sort("place", 1))

        for i in pros:
            plist.append([Button.inline(i['ch'], f'renp{i["pid"]}')])

        await event.edit("选择其类别以重命名：", buttons = plist)
        return

    elif callback.startswith("renp") and user_id in owners:
        rpid = callback[4:]
        ren = products.find_one({"pid": rpid})
        plist = [
            [
                Button.inline('↩️关闭', 'back')]
        ]

        await event.edit(
            f"您正在重命名类别 {ren['ch']} 。\n\n输入新名称：\n例子：\n\n<code>🌍飞机编号✈亚洲号码️tdata|🌍number✈Asian number</code>",
            buttons=plist, parse_mode='html')

        set_step(user_id , f'srename{rpid}')
        return

    elif callback.startswith("irename") and user_id in owners:
        itemid = str(callback[7:]).strip()

        check = items.find_one({"tid": itemid})

        backtid = [[Button.inline('返回↩', f'backtid{check["from_pid"]}')]]

        await event.edit(
            f"""您正在重命名 <b>{check['ch']}</b> 请提交新名称：\n例子：\n\n<code>🌍飞机编号✈美国️tdata|🌍number✈USA number</code>""",
            buttons = backtid, parse_mode='html')

        set_step(user_id , f'irename{itemid}')
        return

    elif callback.startswith("idel") and user_id in owners:
        itemid = str(callback[4:]).strip()

        check = items.find_one({"tid": itemid})

        backtid = [
            [
                Button.inline('是的', f'yesdel{itemid}'.encode()),
                Button.inline('选择退出', f'backtid{check["from_pid"]}'.encode())
            ],
            [
                Button.inline('返回↩', f'backtid{check["from_pid"]}'.encode())
            ]
        ]

        await event.edit(
            f"您想删除按钮 <b>{check['ch']}</b> 吗？",
            buttons=backtid,
            parse_mode='html'
        )

        return

    elif callback.startswith("yesdel") and user_id in owners:
        itemid = str(callback[6:]).strip()

        iti = items.find_one({"tid": itemid})

        items.delete_one({"tid": itemid})

        idems = list(items.find({"from_pid": iti['from_pid']}).sort("place", 1))

        plist = [
            [
                Button.inline('➕新增项目', f"addi{iti['from_pid']}".encode()),
                Button.inline('返回↩', 'backpid')
            ]
        ]

        for i in idems:
            plist.append([Button.inline(i['ch'], f'itim{i["tid"]}'.encode())])

        await event.edit(
            "您可以使用以下按钮删除、添加或更改产品类别:",
            buttons=plist,
            parse_mode='html'
        )

        return

    elif callback.startswith("setprice") and user_id in owners:
        itemid = str(callback[8:]).strip()

        check = items.find_one({"tid": itemid})

        backtid = [[Button.inline('返回↩', f'backtid{check["from_pid"]}')]]

        await event.edit(
            f"""目前设定价格： <b>{check['price']}U</b> 提交新价格：\n例子：\n\n<code>0.8</code>""",
            buttons=backtid, parse_mode='html')

        set_step(user_id , f'setprice{itemid}')

        return

    elif callback.startswith("setprofit") and user_id in owners:
        itemid = str(callback[9:]).strip()

        check = items.find_one({"tid": itemid})

        current_profit = check.get("profitof" , "未设置")

        backtid = [[Button.inline('返回↩', f'backtid{check["from_pid"]}')]]

        await event.edit(
            f"""当前设定利润： <b>{current_profit}U</b> 提交新利润：\n例子：\n\n<code>0.8</code>""",
            buttons=backtid, parse_mode='html')

        set_step(user_id , f'setprofit{itemid}')

        return

    elif callback.startswith("upload") and user_id in owners:
        itemid = str(callback[6:]).strip()

        check = items.find_one({"tid": itemid})

        backtid = [[Button.inline('返回↩', f'backtid{check["from_pid"]}')]]

        await event.edit(
            f"""首先输入该产品的价格和利润：例如\n
<code>1.8\n0.3</code>\n\n第一行是价格，第二行是主要利润""",
            buttons=backtid, parse_mode='html')

        set_step(user_id , f'upload{itemid}')

        return

    elif callback == "backmain" and user_id in owners:
        await event.delete()
        return

    elif callback.startswith("pid") and user_id in owners:
        pid = callback[3:]
        idems = list(items.find({"from_pid": pid}).sort("place", 1))

        plist = [
            [
                Button.inline('➕新增项目', f"addi{pid}".encode()),
                Button.inline('返回↩', 'backpid')
            ]
        ]

        for i in idems:
            plist.append([Button.inline(i['ch'], f'itim{i["tid"]}'.encode())])

        await event.edit(
            "您可以使用以下按钮删除、添加或更改产品类别:",
            buttons=plist,
            parse_mode='html'
        )

        return

    elif callback.startswith("addi") and user_id in owners:
        from_pid = callback[4:]

        back_inline = [
            [Button.inline('返回↩', 'backpid')]
        ]

        await event.edit(
            "输入产品类别中英文名称:\n例如：\n\n<code>🇺🇸美国Tdata|🇺🇸USA tdata</code>\n\n"
            "不要忘记名称以 | 开头。分离",
            buttons=back_inline,
            parse_mode='html'
        )

        set_step(user_id , f"getitemname{from_pid}")

        return

    elif callback.startswith("backpid") and user_id in owners:
        plist = [
            [Button.inline('➕加产品', 'addp'),
             Button.inline('❌删类别', 'delp'),
             Button.inline('↩️后退', 'back')]
        ]

        pros = list(products.find().sort("place", 1))

        for i in pros:
            plist.append([Button.inline(i['ch'], 'pid' + str(i["pid"]))])

        await event.edit(
            "您可以使用以下按钮删除、添加或更改产品类别",
            buttons=plist
        )
        return

    elif callback.startswith("itim") and user_id in owners:
        cods = callback[4:]
        check = items.find_one({"tid": cods})
        pback = [
            [Button.inline('返回↩', 'backtid' + str(check["from_pid"]))],
            [Button.inline('🔁改名', 'irename' + cods),
             Button.inline('❌删除', 'idel' + cods)],
            [Button.inline('⏏️上传文件', 'upload' + cods),
             Button.inline('💠价格变动', 'setprice' + cods)],
            [Button.inline('💸设置利润信息', 'setprofit' + cods)]
        ]

        #dddd = products.find_one({"pid": check['from_pid']})

        await event.edit(f"""<b>这个的状态:

☑️姓名 : {check['ch']}

💴每件价格：{check["price"]} USDT

🔢账户数量： {check["quan"]}

每个号码的利润：{check.get("profitof")}

</b>""",
            buttons=pback,
            parse_mode='html'
        )
        return

    elif callback.startswith("backtid") and user_id in owners:
        pid = callback[7:]
        idems = list(items.find({"from_pid": pid}).sort("place", 1))

        plist = [
            [Button.inline('➕新增项目', 'addi' + pid),
             Button.inline('返回↩', 'backpid')]
        ]

        for i in idems:
            plist.append([Button.inline(i['ch'], 'itim' + str(i["tid"]))])

        await event.edit(
            "您可以使用以下按钮删除、添加或更改产品类别:",
            buttons=plist
        )

        return

    elif callback.startswith("rem") and user_id in owners:
        todel = callback[3:]
        products.delete_one({"pid": todel})

        plist = [
            [Button.inline('➕添加产品', 'addp'),
             Button.inline('❌删除类别', 'delp'),
             Button.inline('↩️后退', 'back')]
        ]

        pros = list(products.find({}).sort("place", 1))

        for i in pros:
            plist.append([Button.inline(i['ch'], 'pid' + str(i["pid"]))])

        await event.edit(
            "所需类别已被删除✅\n\n您可以使用以下按钮删除、添加或更改产品类别",
            buttons=plist
        )

        return

    elif callback.startswith("plac") and user_id in owners:
        plac = callback[4:5]
        code = callback[5:]

        procount = products.count_documents({})

        if int(plac) > procount:
            await event.answer("已完成的排列数再次进入菜单重新排列。", alert=True)
            return

        products.update_one({"pid": code}, {"$set": {"place": int(plac)}})

        pros = list(products.find({}).sort("place", 1))
        inl = [[Button.inline('↩️后退','back')]]

        for i in pros:
            inl.append(
                [Button.inline(f"{i['place']} {i['ch']}", f'plac{int(plac) + 1}{i["pid"]}')])

        await event.edit(f"选择以下按钮确定从显示优先级到结束的顺序:(位置 - {int(plac) + 1})",
                                      buttons=inl)

        return

    elif callback.startswith("tlac") and user_id in owners:
        plac = callback[4:5]
        code = callback[5:]

        procount = items.count_documents({})

        if int(plac) > procount:
            await event.answer("已完成的排列数再次进入菜单重新排列。" , alert=True)
            return

        items.update_one({"tid": code}, {"$set": {"place": int(plac)}})

        pros = list(items.find({}).sort("place", 1))
        inl = [[Button.inline('↩️后退', 'back')]]

        # InlineKeyboardButton('⏪前一阶段', callback_data='back')

        for i in pros:
            inl.append(
                [Button.inline(f"{i['place']} {i['ch']}", f'tlac{int(plac) + 1}{i["tid"]}')])

        await event.edit(f"选择以下按钮确定从显示优先级到结束的顺序:(位置 - {int(plac) + 1})",
                                      buttons=inl)

        return

last_info = {}

async def handle_upload(event, user_step, chat_id , message):
    code = user_step[8:]
    iti = items.find_one({"tid": code})
    ipi = products.find_one({"pid": iti['from_pid']})
    extract_path = os.path.join(ipi['ch'], iti['ch'])

    file = event.document
    uid = event.sender_id
    uname = event.sender.username

    for attr in file.attributes:
        if isinstance(attr, DocumentAttributeFilename):
            file_name = attr.file_name
            break

    file_path = os.path.join("downloads", file_name)

    # تابع callback برای نمایش درصد پیشرفت دانلود
    async def progress_callback(current, total):
        await asyncio.sleep(0.1)
        progress_percentage = (current / total) * 100
        # ارسال پیام با درصد پیشرفت
        await event.respond(f"<b>下载 {progress_percentage:.2f}% </b>", parse_mode='html')

    await asyncio.sleep(0.2)

    # دانلود فایل و اعمال تابع progress_callback
    x = await event.download_media(file_path, progress_callback=progress_callback)

    await asyncio.sleep(0.1)

    # Unzip the file
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(f"{ipi['ch']}/{iti['ch']}")
            file_list = zip_ref.infolist()

            # فیلتر کردن فایل‌هایی که فرمت .txt یا .session دارند
            specific_files = [
                file_info for file_info in file_list
                if file_info.filename.endswith('.txt') or file_info.filename.endswith('.session')
            ]

            # شمارش فایل‌ها با فرمت مشخص
            specific_files_count = len(specific_files)

            # فیلتر کردن فولدرها (اگر فایل زیپ با ساختار فولدر باشد)
            top_level_folders = set()  # استفاده از مجموعه برای جلوگیری از تکرار
            for item in file_list:
                parts = item.filename.split('/')  # مسیر فایل را به بخش‌های جدا تقسیم می‌کنیم
                if len(parts) > 1:  # فقط مسیرهایی که دارای یک فولدر هستند بررسی می‌شوند
                    top_level_folders.add(parts[0])  # فقط فولدر سطح اول اضافه می‌شود

            folders = list(top_level_folders)

            folder_count = len(folders)

        await message.reply(f"文件解压至 {ipi['ch']}/{iti['ch']}")

        if folder_count == 0:
            nin = specific_files_count
        else:
            nin = folder_count

        try:
            pch = f"{ipi['ch']}/{iti['ch']}"
            await bot.send_message(entity=report_charge, message=f"""✅ 新账户上传成功 ✅
👤上传人： @{uname}
🆕上传商品： {ipi['ch']}/{iti['ch']}
🛍商品单价：{iti['price']}U
✅上传数量：{nin}
🟢该商品当前库存：{get_files(pch, False)}
                            """, parse_mode='html')

            data = {"from": uname, "cat": f"{ipi['ch']}/{iti['ch']}", "counts": nin, "time": time.time()}
            uploads.insert_one(data)

        except Exception as e:
            print(e)

        try:
            await bot.send_message(entity=Restock_notification_channel, message=f"""🟢🟢🟢库存更新🟢🟢🟢

🏪分类：{ipi['ch']}
🛍商品：{iti['ch']}
🛒上传数量： {nin} 个
💰单价： {iti['price']}U
🆕当前库存： {get_files(pch, False)} 个
                            """, parse_mode='html', buttons=
            [
                [Button.url("⭕自助提号", url="https://t.me/GXS66666_bot"),
                 Button.url("📞售后客服", url="https://t.me/GXS6666666")]
            ]

                                   )
        except:
            pass

        dic = {"cat": ipi['ch'], "sub": iti['ch'], "count": int(nin), "price": iti['price'], "final": int(get_files(pch , False))}
        asyncio.create_task(loop_news(**dic))

    except zipfile.BadZipFile:
        await message.reply("该文件不是有效的 ZIP 文件。")
    finally:
        os.remove(file_path)

    return

async def _send_files(event, user_step, chat_id , message):
    pass

ext_check = [0]
@bot.on(events.NewMessage())
async def answer(event):
    await asyncio.sleep(0.03)
    if ext_check[0] == 0:
        ext_check[0] = 1
        asyncio.create_task(expire_check())
        asyncio.create_task(check_input_usdt())

    message = event.message

    text = event.raw_text
    chat_id = event.sender_id
    first_name = event.sender.first_name or "none"
    username = event.sender.username
    #---------------------------------
    user = get_user(chat_id) or {}

    is_ban = block.find_one({"userid" : chat_id})
    print(is_ban)
    if is_ban != None:
        return

    user_step = user.get('step') or 'none'

    if text == '🔙返回菜单':
        if user["lang"] == "zh":
            reply = "收费请求已取消"

            await message.reply(reply, buttons=ch_keyboard)
        else:
            reply = "Charge request canceled"

            await message.reply(reply, buttons=en_keyboard)

        set_step(chat_id , "none")
        return

    if text.startswith("+") and len(text) >= 1:
        idems = list(items.find({}).sort("place", 1))

        idems = sorted(idems, key=lambda i: i.get('quan', 0), reverse=True)
        plist = []
        if user["lang"] == "zh":

            for i in idems:
                is_exsit = products.find_one({"pid" : i["from_pid"]})
                if not is_exsit:
                    continue
                if text in i['ch']:
                    quan = i.get('quan') or 0
                    if quan > 0:
                        plist.append([Button.inline(f"{i['ch']}({i['quan']})", f'utem{i["tid"]}')])

            plist.append([Button.inline('❌关闭', f'close'),
                          Button.inline('返回↩', f'backpu')])

            reply = f"""<b>🛒选择你需要的商品：\n❗️没使用过本店商品的，请先少量购买测试，以免造成不必要的争执！谢谢合作</b>"""
            await event.reply(reply, buttons=plist, parse_mode="html")
        else:
            for i in idems:
                if text in i['en']:
                    quan = i.get('quan') or 0
                    if quan > 0:
                        plist.append([Button.inline(f"{i['en']}({i['quan']})", f'utem{i["tid"]}')])

            plist.append([Button.inline('❌Close', f'close'),
                          Button.inline('BACK↩', f'backpu')])

            reply = f"""<b>🛒Choose the product you need:\n❗️If you have not used our products, please buy a small amount to test first to avoid unnecessary disputes! Thank you for your cooperation</b>"""
            await event.reply(reply, buttons=plist, parse_mode="html")
        return

    if text.lower() == '/start':
        if not user:
            data = {"userid": chat_id, "name": first_name[0:10],
                    "username": username, 'total_buy': 0, "balance": 0, "used_balance": 0,
                    "lang": 'zh', "register_time": round(time.time())}
            users.insert_one(data)

            user_lang = "zh"
        else:
            user_lang = user['lang']

        if user_lang == "zh":
            await message.reply(ch_start , parse_mode='html' , buttons = ch_keyboard)
        else:
            await message.reply(en_start, parse_mode='html', buttons=en_keyboard)
        return

    if text.startswith("/report") and chat_id in owners:

        if text == "/report":
            get_report = await collect_report()
        else:
            args = event.raw_text.split()
            time_data = args[1]
            get_report = await collect_report(time_data)

        await message.reply(get_report , parse_mode = "html")
        return

    if text.lower() == '/senter':
        await message.reply(f"{sents[0]}")
        return

    # get inputs
    if user_step == "custom_pay":
        cancel_button = [[Button.text("🔙返回菜单" , resize=True)]]
        await event.delete()
        try:
            data = int(text)
        except:
            if user['lang'] == 'zh':
                await message.reply("号码不正确。输入正确的数字：",buttons = ch_keyboard)
            else:
                await message.reply("Incorrect number . Enter the correct number:",buttons = en_keyboard)
            return

        while True:
            random_number = round(random.uniform(0.001, 0.099), 3)
            amount = data + random_number

            check = payments.find_one({"amount": amount})

            if check == None:
                now_time = round(time.time())
                expires_in = round(time.time()) + 1200

                payments.insert_one(
                    {"amount": amount, "userid": chat_id, "expire": expires_in})

                break
            else:
                continue

        await event.delete()
        qr_address = generate_qr_file(usdt_address)
        if user['lang'] == 'zh':
            await asyncio.sleep(0.2)
            await event.client.send_message(
                event.chat_id,
                file=qr_address,
                message=f"""支付金额：<code>{amount}</code> USDT
收款地址：<code>{usdt_address}</code>

❗️请一定按照金额后面小数点转账，否则未到账概不负责❗️

创建时间：{china_time(now_time)}
结束时间：{china_time(expires_in)}

请在20分钟内支付完成，否则订单失效</b>""",
                parse_mode='html'
            )
        else:
            await asyncio.sleep(0.2)
            await event.client.send_message(
                event.chat_id,
                file=qr_address,
                message=f"""<b>Actual payment amount: <code>{amount}</code> USDT
Receiving Address: <code>{usdt_address}</code>

❗️ Please make sure to transfer the exact amount including decimals, we will not be responsible for any discrepancies due to incorrect amounts ❗️

Creation Time: {china_time(now_time)}
End Time: {china_time(expires_in)}

Please complete the payment within 20 minutes, otherwise the order will expire
</b>
                            """,
                parse_mode='html'
            )

        set_step(chat_id , "none")

        return

    elif user_step.startswith("buy"):
        suds = user_step[3:]

        if text.startswith("购买"):
            numb = text.split(" ")[1].strip()
        else:
            numb = text
        try:
            numb = int(numb)
        except:
            await message.reply("发送号码的格式不正确。再试一次:")
            return

        idems = items.find_one({"tid": suds})

        dddd = products.find_one({"pid": idems['from_pid']})

        await asyncio.sleep(0.2)

        total = get_files(f"{dddd['ch']}/{idems['ch']}", all=False)

        if numb > total:
            if user['lang'] == "zh":

                await message.reply(f"""<b>❌库存不足，请重新选择数量！当前库存为：{total}</b>""", parse_mode='html' , buttons = ch_keyboard)
            else:
                await message.reply(
                    f"""<b>❌Out of stock, please select another quantity! Current inventory is: {total}</b>""",
                    parse_mode='html' , buttons = en_keyboard)
            set_step(chat_id , "none")
            return
        elif numb > 1001:
            if user['lang'] == "zh":

                await message.reply(f"""<b>每个订单的最大数量为 1000</b>""", parse_mode='html' , buttons = ch_keyboard)
            else:
                await message.reply(
                    f"""<b>❌The maximum number of units per order is 1000</b>""",
                    parse_mode='html', buttons = en_keyboard)
            set_step(chat_id, "none")
            return

        full_cost = numb * idems['price']
        #print(user['balance'])
        #print(full_cost)
        # print(full_cost)
        if full_cost > user['balance']:
            if user['lang'] == "zh":
                await message.reply(f"""<b>❌余额不足，请及时充值！</b>""", parse_mode='html' , buttons =ch_keyboard)
            else:
                await message.reply(f"""<b>❌The balance is insufficient, please recharge in time!</b>""",
                                                parse_mode='html', buttons =en_keyboard)
            set_step(chat_id , 'none')
            return

        else:
            if user['lang'] == 'zh':

                inline = [[Button.inline("❌取消购买", "backpu"),
                           Button.inline("✅购买确认", f"acc_{suds}_{numb}")],
                          [Button.inline("↩️主菜单", "backpu")]]
                await message.reply(f"""✅您正在购买:  {idems['ch']}

✅数字：{numb}
💰 价格： {idems['price']} USDT
✅总价：{round(full_cost, 3)} USDT
                    """, buttons =inline, parse_mode='html')
            else:
                inline = [[Button.inline("❌Cancel", "backpu"),
                           Button.inline("✅Accept", f"acc_{suds}_{numb}")],
                          [Button.inline("↩️Back menu", "backpu")]]
                await message.reply(f"""✅You are buying: {idems['ch']}

✅Count: {numb}
💰 Price: {idems['price']} USDT
✅Total price: {round(full_cost, 3)} USDT
                    """, buttons=inline, parse_mode='html')

            set_step(chat_id, 'none')
            return

    elif user_step == "agent":
        # 正则表达式提取token db adminid admin后的内容
        pattern = re.compile(
            r"api_token:([^\n]+)\n"
            r"DB:([^\n]+)\n"
            r"admin_id:([0-9]+)\n"
            r"admin:([^\n]+)",
            re.MULTILINE
        )

        match = pattern.search(text)

        if not match:
            await message.reply("提交格式错误，请务必按照以下格式填写并发送:\n"
                                  "api_token:你的机器人token\n"
                                  "DB:你的机器人用户名\n"
                                  "admin_id:管理员ID\n"
                                  "admin:管理员用户名",
                                  buttons=back_button)
            return

        api_token = match.group(1).strip()
        db_name = match.group(2).strip()
        admin_id = int(match.group(3))
        admin_username = match.group(4).strip()

        # 构建新的agent数据
        new_agent = {
            "api_token": api_token,
            "DB": db_name,
            "admin_id": admin_id,
            "admin": admin_username
        }

        # 读取agents.json
        try:
            with open(AGENTS_FILE, "r", encoding="utf-8") as f:
                agents_data = json.load(f)
        except FileNotFoundError:
            # 文件不存在则创建
            agents_data = {"users": []}
        except json.JSONDecodeError:  # JSON 文件解析错误
            await message.reply("agents.json 文件损坏，请检查文件内容。")
            return

        # 将新的agent添加到json数据中
        agents_data["users"].append(new_agent)

        # 写回agents.json
        try:
            with open(AGENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(agents_data, f, indent=2, ensure_ascii=False) #ensure_ascii=False 防止中文乱码
        except Exception as e:
            await message.reply(f"写入 agents.json 文件失败: {e}")
            return

        if user['balance'] >= agent_price:
            try:
                await bot.send_message(entity=clone_report, message=f"""<b>⭕️请求激活机器人
    🔹来自用户：<a href="tg://user?id={chat_id}">{chat_id}</a>
    🔸用户名：@{username}
    ---------------------------
    🔹提交信息:\n\n{text}</b>""", parse_mode='html')

                newbl = user['balance'] - agent_price
                users.update_one({"userid": chat_id}, {"$set": {"balance": newbl}})

                await message.reply("<b>✅✅您的机器人将在5分内激活。有任何问题或疑问，您请联系：@GXS6666666</b>",
                                            buttons=ch_keyboard, parse_mode='html', link_preview=False)
                set_step(chat_id, 'none')
                return

            except Exception as e:
                await message.reply(f"<b>发生错误 {e}</b>",
                                buttons=ch_keyboard, parse_mode='html')
                set_step(chat_id, 'none')
                return
        else:
            await message.reply(f"<b>您的余额不足，将你的余额增加到{agent_price} U</b>",
                            buttons=ch_keyboard, parse_mode='html')
            set_step(chat_id, 'none')
            return

    elif user_step.startswith("sendfile"):
        if event.document:
            set_step(chat_id, "none")

            asyncio.create_task(handle_upload(event, user_step, chat_id , message))
        else:
            set_step(chat_id , "none")
            await message.reply("获取错误 ZIP" , buttons=ch_keyboard)
            return

    elif user_step.startswith("upload"):
        itemid = str(user_step[6:]).strip()
        try:

            price = float(text.split("\n")[0])
            item_profit = float(text.split("\n")[1])
        except:
            set_step(chat_id, "none")
            await message.reply("输入格式错误，请重试 !", buttons=ch_keyboard)
            return

        items.update_one({"tid" : itemid} , {"$set" : {"price" : price , "profitof" : item_profit}})

        await event.respond(f"原价：{price}U\n利润率：{item_profit}U\n\n发送您的 zip 文件", buttons=[[Button.text('🔙返回菜单', resize=True)]])

        set_step(chat_id, f'sendfile{itemid}')
        return

    elif user_step == "getsubname":
        if '|' not in text:
            await event.respond("-未知的命令。再试一次!", buttons=[[Button.text('🔙返回菜单', resize=True)]])
            return
        ch, en = map(str.strip, text.split('|', 1))

        if create_directory(f"{ch}"):
            pass
        else:
            await event.respond("未知的命令。再试一次!", buttons=[[Button.text('🔙返回菜单', resize=True)]])
            return

        set_step(chat_id, 'none') # none

        products.insert_one({"pid": id_generator(), "ch": ch, "en": en, "place": 0})

        await event.respond("类别名称已设置✅")

        plist = [
            [Button.inline('➕加类别', 'addp'), Button.inline('❌删类别', 'delp')],
            [Button.inline('🔁改名', 'renp'), Button.inline('↩️后退', 'back')]
        ]

        pros = list(products.find().sort("place", 1))

        for i in pros:
            plist.append([Button.inline(i['ch'], f'pid{i["pid"]}')])

        await event.respond("您可以使用以下按钮删除、添加或更改产品类别", buttons=plist)
        return

    elif user_step.startswith("srename"):
        if '|' not in text:
            await event.respond(
                "输入错误。您必须使用正确的格式 e.g. \n<code>🌍飞机编号✈印度尼西亚️tdata|🌍number✈Indonesiatdata</code>",
                buttons=[[Button.text('🔙返回菜单', resize=True)]], parse_mode='html'
            )
            return

        ch, en = map(str.strip, text.split('|', 1))

        code = user_step[7:].strip()

        getold = products.find_one({"pid": code})

        if rename_directory(getold['ch'], ch):
            pass
        else:
            await event.respond("未知的命令。再试一次!", buttons=[[Button.text('🔙返回菜单', resize=True)]])
            return

        set_step(chat_id, 'none')  # none

        products.update_one({"pid": code}, {"$set": {"ch": ch, "en": en}})

        await event.respond("类别名称已设置✅")

        plist = [
            [Button.inline('➕加类别', 'addp'), Button.inline('❌删类别', 'delp')],
            [Button.inline('🔁改名', 'renp'), Button.inline('↩️后退', 'back')]
        ]

        pros = list(products.find().sort("place", 1))

        for i in pros:
            plist.append([Button.inline(i['ch'], f'pid{i["pid"]}')])

        await event.respond("您可以使用以下按钮删除、添加或更改产品类别", buttons=plist)

        return

    elif user_step.startswith("getitemname"):
        if '|' not in text:
            await event.respond(
                "你来自 | 你没有使用",
                buttons=[[Button.text('🔙返回菜单', resize=True)]]
            )
            return

        ch, en = map(str.strip, text.split('|', 1))

        last_info[chat_id] = {'ch' : ch , 'en' : en}

        edata = user_step[11:].strip()

        prod = products.find_one({"pid": edata})

        if create_directory(f"{prod['ch']}/{ch}"):
            pass
        else:
            await event.respond("未知的命令。再试一次!.", buttons=[[Button.text('🔙返回菜单', resize=True)]])
            return

        set_step(chat_id , f"getprice{edata}")
        await event.respond("输入每件的价格：", buttons=[[Button.text('🔙返回菜单', resize=True)]])
        return

    elif user_step.startswith("getprice"):
        text = event.raw_text.strip()
        uid = event.sender_id

        try:
            count = float(text)
        except ValueError:
            await event.respond("输入的号码不正确!", buttons=[[Button.text('🔙返回菜单', resize=True)]])
            return

        edata = user_step[8:].strip()

        items.insert_one({
            "tid": id_generator(),
            "from_pid": edata,
            "ch": last_info[chat_id]["ch"],
            "en": last_info[chat_id]['en'],
            'price': count,
            "place": 0
        })

        set_step(chat_id , 'none')

        await event.respond("类别名称已设置✅")

        idems = list(items.find({"from_pid": edata}).sort("place", 1))

        plist = [
            [Button.inline('➕新增项目', data=f'addi{edata}'),
             Button.inline('返回↩', data='backpid')]
        ]

        for i in idems:
            plist.append([Button.inline(i['ch'], data=f'itim{i["tid"]}')])

        await event.respond("您可以使用以下按钮删除、添加或更改产品类别:", buttons=plist)

        last_info.clear()

    elif user_step.startswith("setprice"):
        code = user_step[8:]  # Extract code

        try:
            price = float(text)
        except ValueError:
            await event.respond("未知的命令。再试一次!", buttons=[[Button.text('🔙返回菜单', resize=True)]])
            return

        iti = items.find_one({"tid": code})

        items.update_one({"tid": code}, {"$set": {"price": price}})

        await event.respond("类别名称已设置✅")

        set_step(chat_id , 'none')

        plist = [
            [Button.inline('➕新增项目', data=f"addi{iti['from_pid']}"),
             Button.inline('返回↩', data='backpid')]
        ]

        pros = list(items.find({"from_pid": iti['from_pid']}).sort("place", 1))

        for i in pros:
            plist.append([Button.inline(i['ch'], data=f'itim{i["tid"]}')])

        await event.respond("您可以使用以下按钮删除、添加或更改产品类别", buttons=plist)

        last_info.clear()

        return

    elif user_step.startswith("setprofit"):
        code = user_step[9:]  # Extract code

        try:
            profitz = float(text)
        except ValueError:
            await event.respond("未知的命令。再试一次!", buttons=[[Button.text('🔙返回菜单', resize=True)]])
            return

        iti = items.find_one({"tid": code})

        items.update_one({"tid": code}, {"$set": {"profitof": profitz}})

        await event.respond("类别名称已设置✅")

        set_step(chat_id , 'none')

        plist = [
            [Button.inline('➕新增项目', data=f"addi{iti['from_pid']}"),
             Button.inline('返回↩', data='backpid')]
        ]

        pros = list(items.find({"from_pid": iti['from_pid']}).sort("place", 1))

        for i in pros:
            plist.append([Button.inline(i['ch'], data=f'itim{i["tid"]}')])

        await event.respond("您可以使用以下按钮删除、添加或更改产品类别", buttons=plist)

        last_info.clear()

        return

    elif user_step.startswith("irename"):
        if '|' not in text:
            await event.respond(
                f"""输入错误。您必须使用正确的格式 e.g. \n<code>🌍飞机编号✈印度尼西亚️tdata|🌍number✈usa tdata</code>""",
                buttons=[[Button.text('🔙返回菜单', resize=True)]], parse_mode='html'
            )
            return

        ch = text.split('|')[0].strip()
        en = text.split('|')[1].strip()

        code = user_step[7:]

        iti = items.find_one({"tid": code})
        ipi = products.find_one({"pid": iti['from_pid']})

        if rename_directory(f"{ipi['ch']}/{iti['ch']}", f"{ipi['ch']}/{ch}"):
            pass
        else:
            await event.respond(
                "未知的命令。再试一次!", buttons=[[Button.text('🔙返回菜单', resize=True)]])
            return

            # Update the item information in the database
        items.update_one({"tid": code}, {"$set": {"ch": ch, "en": en}})

        await event.respond("类别名称已设置✅")

        set_step(chat_id , 'none')

        plist = [
            [Button.inline('➕新增项目', data=f"addi{iti['from_pid']}"),
             Button.inline('返回↩', data='backpid')]
        ]

        pros = list(items.find({"from_pid": iti['from_pid']}).sort("place", 1))

        for i in pros:
            plist.append([Button.inline(i['ch'], data=f'itim{i["tid"]}')])

        await event.respond("您可以使用以下按钮删除、添加或更改产品类别", buttons=plist)

        last_info.clear()

        return

    elif text == "📱联系客服" or text == "📱Contact Me":
        if user['lang'] == "zh":
            reply = ch_support
        else:
            reply = en_support
        await message.reply(reply , parse_mode = 'html')

        return

    elif text == "🛒商品列表" or text == "🛒Product List":
        lang = get_user(chat_id)

        pros = list(products.find({}).sort("place", 1))
        inline_buttons = []

        #pros = sorted(pros, key=lambda i: i.get('quan', 0), reverse=True)

        if lang["lang"] == "zh":

            for i in pros:
                #if i['quan'] > 0:
                    inline_buttons.append([Button.inline(f"{i['ch']}({i['quan']})", f'subpid{i["pid"]}')])

            inline_buttons.append([Button.inline(f"❌关闭", f'cancel_pid')])

            reply = f"""<b>🛒选择你需要的商品：\n❗️先少量购买测试，谢谢合作</b>"""
            await message.reply(reply,buttons=inline_buttons , parse_mode="html")

        else:
            for i in pros:
                inline_buttons.append([Button.inline(f"{i['ch']}({i['quan']})", f'subpid{i["pid"]}')])

            inline_buttons.append([Button.inline(f"❌关闭", f'cancel_pid')])

            reply = f"""<b>🛒 Choose the items you need:\n❗️ Please make a small test purchase firs! Thank you for your cooperation</b>"""

            await message.reply(reply, buttons=inline_buttons, parse_mode="html")

        return

    elif text == "🌐中文语言" or text == "🌐English":
        if user['lang'] == 'zh':
            users.update_one({"userid": chat_id}, {"$set": {'lang': 'en'}})
            await message.reply("Switch language successful", parse_mode='html',buttons=en_keyboard)
        else:
            users.update_one({"userid": chat_id}, {"$set": {'lang': 'zh'}})
            await message.reply("切换语言成功",parse_mode='html',buttons=ch_keyboard)
        return

    elif text == "🧍‍♂️️用户中心" or text == '🧍‍♂️️User Center':
        if user['lang'] == "zh":
            reply = f"""<b>您的ID:  <code>{chat_id}</code>
您的户名:  <a href="http://t.me/{username}">{username or ''}</a>
注册日期:  {china_time(user["register_time"])}
总购数量:  {user["total_buy"]}
您的余额:  {round(user['balance'],3)} USDT
总购金额: {round(user['used_balance'],3)} USDT</b>"""

            button_text = "☎️ 售后客服"
        else:
            reply = f"""<b>Your ID:  <code>{chat_id}</code>
Your username:  <a href="http://t.me/{username}">{username or ''}</a>
Registration date:  {china_time(user["register_time"])}
Total purchase quantity:  {user["total_buy"]}
Your balance: {round(user['balance'], 3)} USDT
Total purchase amount:  {user['used_balance']} USDT</b>
                            """
            button_text = "📱Contact Me"

        contact_inline = [[Button.url(button_text, url=f"https://t.me/{support}")]]

        await message.reply(reply,buttons=contact_inline,parse_mode = 'html', link_preview=False)

        return

    elif text == "🔹Buy history" or text == "🔹购买记录":
        get_data = list(sales.find({"user": chat_id}).sort("time", DESCENDING).limit(20))
        orders = []
        for i in get_data:
            if i.get("zname") != None:
                download = f"下载文件 ➡️ /downl_{i['zname']}"
                download = download.split(".")[0]
            else:
                download = ""

            matn = f"""⭕️ 分类 ：{i['cat']}
🔰总账号数 ：{i['total_accounts']}
💰花费 ：{round(i['cost'], 3)} U
🕔购买时间：{china_time(i['time'])}
{download}
➖➖➖➖➖➖➖➖➖"""
            orders.append(matn)

        add_text = "\n".join(orders)
        await message.reply(f"""<b>您的最近 20 个订单：\n\n{add_text}
                </b>""", parse_mode='html')

        return

    elif text.startswith("/downl_"):
        fileid = text[7:]

        t_id = fileid.split("_")[1]
        if str(chat_id) == str(t_id):
            try:
                await asyncio.sleep(0.2)
                await bot.send_file(entity=chat_id, file=f"sold/{fileid}.zip")

            except:
                await message.reply("找不到文件")

        return

    elif text == "🤝商店克隆":
        active_clone = [[Button.inline("📹 演示视频", "active_video"),
                         Button.inline("🤖创建机器人", "active_clone"),
                         Button.inline("开始克隆","active_token")]]

        await message.reply(f"""<b>欢迎加入代理系统
！！！！请务必开通前联系客户否则费用加倍！！！！
一键克隆拥有同款机器人
共享仓库，每笔销售都会自动结算利润
1、商品定价
你可以自定利润（比如在我的价格基础上上浮0.05-0.4U）
2、商品补货和库存
总部机器人的仓库里面有多少账号，你的机器人里就会有多少账号，补货由我们统一进行
如果你有自己的账号想上架，可以联系我们的客服进行商谈，价格合适且账号质量检查后没有问题我们会上传到机器人
3、机器人上的充值地址
使用总部统一的地址
4、售后问题
新功能：机器人会对用户购买的账户进行自动检测，并根据检测结果退还死号账户的余额给用户。
5、克隆费用
280U，永久售后，与总部机器人功能同步更新
同时你可以供别人来进行克隆挣取利上利

点击下方按钮观看演示视频，当你准备好以后，拥有不低于280U的余额，以便扣费能够顺利进行，然后点击下方按钮“创建机器人”即可。</b>
        """, parse_mode='html', buttons = active_clone)
        return

    elif text == "💳充值余额" or text == "💳Recharge":
        inline_buttons = [
            [
                Button.inline("5U", "usd5"),
                Button.inline("10U", "usd10"),
                Button.inline("20U", "usd20"),
                Button.inline("50U", "usd50"),
            ],
            [
                Button.inline("100U", "usd100"),
                Button.inline("300U", "usd300"),
                Button.inline("500U", "usd500"),
                Button.inline("1000U", "usd1000"),
            ],
            [
                Button.inline("自定金额-custom pay", "custom"),
                Button.inline("取消充值-cancel", "cancel"),
            ],
        ]

        if user['lang'] == 'zh':
            reply = """<b>💰请选择下面充值订单金额 

💹点击对应金额 请严格按照提示小数点转账‼️</b>"""
        else:
            reply = """<b>💰 Please select the recharge order amount below

💹 Please transfer the exact amount‼️</b>"""

        await message.reply(reply, buttons=inline_buttons,parse_mode='html')

        return

    elif text.lower() == "/admin" and chat_id in owners:
        admin_keyboard = [
            [Button.text("ℹ️商店统计"), Button.text("🔙后退")],
            [Button.text("🛒产品列表"), Button.text("👥通知群发")],
            [Button.text("🔁按键排列"), Button.text("🔁产品布局")]
        ]
        message_text = (
            "欢迎使用机器人管理系统\n\n"
            "<b>🔍 搜索用户信息：</b> <code>/info UID</code>\n"
            "<b>💰 增加或减少用户余额：</b> <code>/bal UID +/-AMOUNT</code>\n"
            "   例如: <code>/bal 12343344 +40</code>\n"
            "<b>📊 报告所有用户：</b> <code>/users</code>\n"
        )

        await bot.send_message(
            chat_id,
            message_text,
            buttons=admin_keyboard,
            parse_mode='html'
        )

        return

    elif text.lower() == "ℹ️商店统计" and chat_id in owners:
        total_users = users.count_documents({})

        twenty_four_hours_ago = datetime.datetime.now() - datetime.timedelta(days=1)
        timestamp_24_hours_ago = int(twenty_four_hours_ago.timestamp())
        user24 = users.count_documents({"register_time": {"$gt": timestamp_24_hours_ago}})

        twenty_7d_hours_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        timestamp_7d_hours_ago = int(twenty_7d_hours_ago.timestamp())
        user7d = users.count_documents({"register_time": {"$gt": timestamp_7d_hours_ago}})

        total_buys = 0
        usr = list(users.find({}))
        for i in usr:
            total_buys += i.get('total_buy') or 0

        totalpays = payments.count_documents({"status": 2})

        total_usd = 0
        pyr = list(payments.find({"status": 2}))
        for x in pyr:
            total_usd += x['amount']
        total_usd = round(total_usd, 3)

        count_pays = 0
        amount_pays = 0

        for y in pyr:
            if y.get('paid_time') == None:
                continue
            paytime = int(y['paid_time']) // 1000
            last24 = time.time() - 86400
            if paytime >= last24:
                count_pays += 1
                amount_pays += y['amount']

        text = f"""<b>🛑机器人状态：
✅机器人状态：活跃
👥机器人用户总数：{total_users}
👥近24小时内用户数：{user24}
👥近7天新增用户数：：{user7d}
🏧购买总数：{total_buys}至
💸付款总数: {totalpays}至
💰支付总额：{total_usd}U
🌐过去24小时内收到的金额：{amount_pays}U
🔆参赛作品数量：{count_pays} 付款

</b>
        """
        await message.reply(text, parse_mode='html')
        return

    elif text.lower() == "🛒产品列表" and chat_id in owners:
        plist = [
            [
                Button.inline('➕加类别', 'addp'),
                Button.inline('❌删类别', 'delp'),
                Button.inline('🔁改名', 'renp'),
                Button.inline('↩️后退', 'back_admin')
            ]
        ]

        pros = list(products.find().sort("place", 1))

        for i in pros:
            plist.append([Button.inline(i['ch'], f'pid{i["pid"]}'.encode())])

        await event.respond(
            "您可以使用以下按钮删除、添加或更改产品类别",
            buttons=plist
        )

        return

    elif text.lower() == "🔙后退" and chat_id in owners:
        await message.reply("返回主菜单",buttons=ch_keyboard)
        return

    elif text.lower() == "👥通知群发" and chat_id in owners:
        await message.reply(f"""发送您的短信：""")
        set_step(chat_id , "msgall")
        return

    elif text.lower() == "🔁按键排列" and chat_id in owners:
        pros = list(products.find({}).sort("place", 1))
        inl = [[Button.inline('↩️后退', 'back')]]

        # InlineKeyboardButton('⏪前一阶段', callback_data='back')

        for i in pros:
            inl.append([Button.inline(f"{i['place']} {i['ch']}", f'plac1{i["pid"]}')])

        await message.reply("选择以下按钮确定从显示优先级到结束的顺序:(位置 - 1)", buttons = inl)

        return

    elif text.lower() == "🔁产品布局" and chat_id in owners:
        idem = list(items.find({}).sort("place", 1))
        inl = [[Button.inline('↩️后退', 'back')]]

        # InlineKeyboardButton('⏪前一阶段', callback_data='back')

        for i in idem:
            inl.append([Button.inline(f"{i['place']} {i['ch']}", f'tlac1{i["tid"]}')])

        await message.reply("选择以下按钮确定从显示优先级到结束的顺序:(位置 - 1)", buttons=inl)

        return

    elif text.lower() == "/users" and chat_id in owners:
        users_with_balance = list(users.find({"balance": {"$ne": 0}}).sort("balance", -1))

        allbl = 0
        for x in users_with_balance:
            allbl += x.get('balance') or 0

        text = [f"🛑所有用户总余额：{allbl}u\n"]
        for i in users_with_balance:
            text.append(
                f'{int(i["userid"])} - <a href="tg://user?id={int(i["userid"])}">{i["name"]}</a> 余额：{round(i.get("balance") or 0, 3)}U')

        newtxt = "\n\n".join(text)
        await message.reply(newtxt, parse_mode='html')
        return

    if text.lower() == '/block' and chat_id in owners:
        args = event.raw_text.split()
        if len(args) > 1:
            userid = args[1]
            info = users.find_one({"userid": int(userid)})
            is_block = block.find_one({"userid": int(userid)})
            if info is None:
                await event.respond("未找到用户")
                return
            if info is None:
                block.insert_one({"userid" : int(userid)})
                await message.reply("done")

        await message.reply("OK")
        return

    if text.lower() == '/unblock' and chat_id in owners:
        args = event.raw_text.split()
        if len(args) > 1:
            userid = args[1]
            info = users.find_one({"userid": int(userid)})
            is_block = block.find_one({"userid": int(userid)})
            if info is None:
                await event.respond("未找到用户")
                return
            if info != None:
                block.delete_one({"userid": int(userid)})
                await message.reply("done")

        await message.reply("OK")
        return

    elif text.startswith("/info") and chat_id in owners:
        args = event.raw_text.split()
        if len(args) > 1:
            userid = args[1]
            info = users.find_one({"userid": int(userid)})
            if info is None:
                await event.respond("未找到用户")
                return

            await event.respond(f"""
🔹 ID : {userid} - @{info['username']}
🔹用户库存 :  {info['balance']}U
🔹用过的： {info['used_balance']}U
🔹购买数量 :  {info['total_buy']}
注册日期 : {china_time(info["register_time"])}
        """)

    elif text.startswith("/bal") and chat_id in owners:

        args = event.raw_text.split(maxsplit=3)  # Split into max 3 parts: /bal, userid, amount, message

        if len(args) < 3:
            await event.respond("⚠️ 格式错误！正确格式: `/bal <用户ID> <金额> [消息]`")

            return

        userid = args[1]

        try:

            bals = float(args[2])  # Convert balance change to float

        except ValueError:

            await event.respond("⚠️ 请输入有效的数字金额！")

            return

        message = args[3] if len(args) > 3 else ""  # Optional message

        try:

            user = users.find_one({"userid": int(userid)})

        except:

            await event.respond("❌ 未找到用户!")

            return

        if not user:
            await event.respond("❌ 未找到用户!")

            return

        new_balance = user['balance'] + bals

        users.update_one({"userid": int(userid)}, {"$set": {'balance': new_balance}})

        message_text = (

f"<b>🔹 {bals} U 已从您的账户中扣除。\n余额：{round(new_balance, 3)} U</b>\n\n<b>{message}</b>"

if bals < 0 else

f"<b>🔹 {bals} U 已添加到您的帐户。\n当前：{round(new_balance, 3)} U</b>\n\n<b>{message}</b>"

        )
        try:
            await bot.send_message(entity=int(userid), message=message_text, parse_mode='html')
        except:
            pass

        await event.respond(f"<b>✅ 用户 {userid} 的余额已更新：{round(new_balance, 3)} U</b>", parse_mode='html')
        return

    elif user_step == "msgall":
        set_step(chat_id , 'none')

        await message.reply("已发出发送给用户的请求")

        asyncio.create_task(send_to_all(text , chat_id))
        return

threading.Thread(target=update_products_counts, args=()).start()

while True:
    try:
        bot.run_until_disconnected()
    except:
        continue