import os
import json
import random
import uuid
from datetime import datetime
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

TOKEN = os.getenv("TOKEN")  # 在 Replit Secrets 设置 BOT Token

# 钱包数据处理
def load_data():
    if not os.path.exists("data.json"):
        with open("data.json", "w") as f:
            f.write("{}")
    with open("data.json", "r") as f:
        return json.load(f)

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f)

# 红包数据处理
def load_all_red_packets():
    if not os.path.exists("red_packets.json"):
        with open("red_packets.json", "w") as f:
            json.dump({"red_packets": []}, f)
    with open("red_packets.json", "r") as f:
        return json.load(f).get("red_packets", [])

def save_all_red_packets(packets):
    with open("red_packets.json", "w") as f:
        json.dump({"red_packets": packets}, f)

def save_red_packet(packet):
    packets = load_all_red_packets()
    packets.append(packet)
    save_all_red_packets(packets)

# /start 初始化用户
def start(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {
            "wallet": 100,  # 初始化钱包字段
            "last_checkin": ""
        }
        save_data(data)
    update.message.reply_text(f"欢迎来到红包游戏！你当前余额是 {data[user_id]['wallet']} 金币")

# /balance 查看余额
def balance(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    data = load_data()
    bal = data.get(user_id, {}).get("wallet", 0)
    update.message.reply_text(f"你的余额是 {bal} 金币")

# /send_red_packet 金额 份数
def send_red_packet(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    args = context.args

    if len(args) != 2:
        update.message.reply_text("用法：/send_red_packet 金额 份数\n例如：/send_red_packet 100 5")
        return

    try:
        total = int(args[0])
        count = int(args[1])
    except ValueError:
        update.message.reply_text("请输入数字")
        return

    if total <= 0 or count <= 0 or total < count:
        update.message.reply_text("金额或份数不合法")
        return

    data = load_data()
    if data.get(user_id, {}).get("wallet", 0) < total:
        update.message.reply_text("余额不足")
        return

    data[user_id]["wallet"] -= total
    save_data(data)

    packet_id = str(uuid.uuid4())[:8]
    red_packet = {
        "packet_id": packet_id,
        "sender_id": user_id,
        "total": total,
        "remaining": total,
        "count": count,
        "grabbed": {}
    }

    save_red_packet(red_packet)
    update.message.reply_text(
        f"你已发送一个拼手气红包，总金额 {total} 金币，共 {count} 份！\n"
        f"其他人可使用 /grab_red_packet {packet_id} 抢红包"
    )

# /grab_red_packet 红包ID
def grab_red_packet(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    args = context.args

    if len(args) != 1:
        update.message.reply_text("用法：/grab_red_packet 红包ID")
        return

    packet_id = args[0]
    packets = load_all_red_packets()

    for rp in packets:
        if rp["packet_id"] == packet_id:
            if user_id in rp["grabbed"]:
                update.message.reply_text(f"你已抢过，抢到 {rp['grabbed'][user_id]} 金币")
                return

            if rp["count"] <= 0 or rp["remaining"] <= 0:
                update.message.reply_text("红包已被抢完")
                return

            if rp["count"] == 1:
                amount = rp["remaining"]
            else:
                max_grab = rp["remaining"] // rp["count"] * 2
                amount = random.randint(1, max(1, max_grab))

            rp["grabbed"][user_id] = amount
            rp["remaining"] -= amount
            rp["count"] -= 1
            save_all_red_packets(packets)

            data = load_data()
            if user_id not in data:
                data[user_id] = {"wallet": 0, "last_checkin": ""}
            data[user_id]["wallet"] += amount
            save_data(data)

            update.message.reply_text(f"你抢到了 {amount} 金币！")
            return

    update.message.reply_text("红包不存在")

# /red_packet_list 查看可抢红包
def red_packet_list(update: Update, context: CallbackContext):
    packets = load_all_red_packets()
    msg = "当前可抢红包列表：\n"
    active = 0
    for rp in packets:
        if rp["count"] > 0 and rp["remaining"] > 0:
            active += 1
            msg += (
                f"红包ID: {rp['packet_id']} | 剩余份数: {rp['count']} | 剩余金额: {rp['remaining']}\n"
            )

    if active == 0:
        msg = "目前没有可抢的红包。"

    update.message.reply_text(msg)

# /transfer 用户ID 金额
def transfer(update: Update, context: CallbackContext):
    sender_id = str(update.effective_user.id)
    args = context.args

    if len(args) != 2:
        update.message.reply_text("用法：/transfer 用户ID 金额\n例如：/transfer 123456789 50")
        return

    recipient_id = args[0]
    try:
        amount = int(args[1])
    except ValueError:
        update.message.reply_text("金额必须是数字")
        return

    if amount <= 0:
        update.message.reply_text("金额必须大于0")
        return

    data = load_data()

    # 确保发件人和收件人都初始化了钱包
    if sender_id not in data:
        data[sender_id] = {"wallet": 0, "last_checkin": ""}
    if recipient_id not in data:
        data[recipient_id] = {"wallet": 0, "last_checkin": ""}

    if data[sender_id]["wallet"] < amount:
        update.message.reply_text("你的余额不足")
        return

    data[sender_id]["wallet"] -= amount
    data[recipient_id]["wallet"] += amount
    save_data(data)

    update.message.reply_text(f"成功向用户 {recipient_id} 转账 {amount} 金币")

# /checkin 每日签到
def checkin(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    data = load_data()

    if user_id not in data:
        data[user_id] = {"wallet": 0, "last_checkin": ""}

    if data[user_id]["last_checkin"] == today:
        update.message.reply_text("你今天已经签到过了，请明天再来！")
    else:
        data[user_id]["wallet"] += 10
        data[user_id]["last_checkin"] = today
        save_data(data)
        update.message.reply_text("签到成功！你获得了10金币")

# /guess 大小 金额
def guess(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    args = context.args

    if len(args) != 2:
        update.message.reply_text("用法：/guess 大小 金额\n例如：/guess 大 50")
        return

    bet = args[0]
    try:
        amount = int(args[1])
    except ValueError:
        update.message.reply_text("金额必须是数字")
        return

    if amount <= 0:
        update.message.reply_text("金额必须大于0")
        return

    data = load_data()

    if data.get(user_id, {}).get("wallet", 0) < amount:
        update.message.reply_text("你的余额不足")
        return

    # 随机生成结果
    result = random.choice(["大", "小"])

    if result == bet:
        data[user_id]["wallet"] += amount
        save_data(data)
        update.message.reply_text(f"恭喜你，猜对了！结果是 {result}，你赢得了 {amount} 金币")
    else:
        data[user_id]["wallet"] -= amount
        save_data(data)
        update.message.reply_text(f"很遗憾，猜错了。结果是 {result}，你损失了 {amount} 金币")

# /leopard 金额
def leopard(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    args = context.args

    if len(args) != 1:
        update.message.reply_text("用法：/leopard 金额\n例如：/leopard 50")
        return

    try:
        amount = int(args[0])
    except ValueError:
        update.message.reply_text("金额必须是数字")
        return

    if amount <= 0:
        update.message.reply_text("金额必须大于0")
        return

    data = load_data()

    if data.get(user_id, {}).get("wallet", 0) < amount:
        update.message.reply_text("你的余额不足")
        return

    # 随机生成豹子结果
    result = random.choice([True, False])  # True 表示豹子，False 表示非豹子

    if result:
        data[user_id]["wallet"] += amount
        save_data(data)
        update.message.reply_text(f"恭喜你，猜对了豹子！你赢得了 {amount} 金币")
    else:
        data[user_id]["wallet"] -= amount
        save_data(data)
        update.message.reply_text(f"很遗憾，没猜对。你损失了 {amount} 金币")

# /userid 查看用户ID
def userid(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    update.message.reply_text(f"你的用户ID是：{user_id}")

# 启动机器人
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("balance", balance))
    dp.add_handler(CommandHandler("send_red_packet", send_red_packet))
    dp.add_handler(CommandHandler("grab_red_packet", grab_red_packet))
    dp.add_handler(CommandHandler("red_packet_list", red_packet_list))
    dp.add_handler(CommandHandler("transfer", transfer))
    dp.add_handler(CommandHandler("checkin", checkin))
    dp.add_handler(CommandHandler("guess", guess))
    dp.add_handler(CommandHandler("leopard", leopard))
    dp.add_handler(CommandHandler("userid", userid))  # 添加查看用户ID命令

    print("Bot started.")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()