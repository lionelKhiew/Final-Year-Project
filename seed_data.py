import pandas as pd
import random
from faker import Faker
from sqlalchemy import create_engine
import datetime

# 1. 配置数据库连接 (注意：我们在 Windows 上运行此脚本，所以用 localhost)
DB_URI = "postgresql://admin:password123@localhost:5432/banking_system"
engine = create_engine(DB_URI)
fake = Faker()

print("🚀 开始生成模拟银行数据...")

# ==========================================
# 2. 生成客户数据 (Customers)
# ==========================================
NUM_CUSTOMERS = 100
customers = []

for i in range(1, NUM_CUSTOMERS + 1):
    # 逻辑：有些客户很有钱，有些很穷
    balance = round(random.uniform(100.0, 50000.0), 2)
    age = random.randint(18, 70)

    # 逻辑：如果存款低于 1000，流失风险(Churn Risk) 设为 High，否则 Low
    # 这样你的 Agent 分析出来的结果才会有规律！
    if balance < 1000:
        churn_risk = "High"
    elif balance < 5000:
        churn_risk = "Medium"
    else:
        churn_risk = "Low"

    customers.append(
        {
            "customer_id": i,
            "name": fake.name(),
            "age": age,
            "account_balance": balance,
            "churn_risk": churn_risk,
            "join_date": fake.date_between(start_date="-2y", end_date="today"),
        }
    )

df_customers = pd.DataFrame(customers)
# 写入数据库 (如果表存在则替换)
df_customers.to_sql("customers", engine, if_exists="replace", index=False)
print(f"✅ 成功插入 {NUM_CUSTOMERS} 位客户。")

# ==========================================
# 3. 生成交易数据 (Transactions)
# ==========================================
NUM_TRANSACTIONS = 500
transactions = []

for _ in range(NUM_TRANSACTIONS):
    # 随机挑一个倒霉客户
    cust_id = random.randint(1, NUM_CUSTOMERS)

    # 随机生成交易类型
    t_type = random.choice(["Deposit", "Withdrawal", "Payment", "Transfer"])

    # 生成金额 (取款是负数)
    amount = round(random.uniform(10.0, 2000.0), 2)
    if t_type in ["Withdrawal", "Payment"]:
        amount = -amount

    transactions.append(
        {
            "customer_id": cust_id,
            "amount": amount,
            "trans_date": fake.date_between(start_date="-1y", end_date="today"),
            "trans_type": t_type,
        }
    )

df_transactions = pd.DataFrame(transactions)
df_transactions.to_sql(
    "transactions", engine, if_exists="replace", index=False, index_label="trans_id"
)
print(f"✅ 成功插入 {NUM_TRANSACTIONS} 条交易记录。")

print("🎉 数据库填充完毕！你的 Agent 有活干了。")
