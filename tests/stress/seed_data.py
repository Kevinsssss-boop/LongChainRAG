"""
Seed test data for stress testing:
- Create 120 test users (stresstest_0 through stresstest_119)
- Upload 5 test documents to knowledge base via admin account
"""
import sys
import os
import httpx

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

TARGET_HOST = os.environ.get("STRESS_TARGET_HOST", "http://localhost:8000")
TEST_USER_PREFIX = "stresstest"
TEST_USER_PASSWORD = "TestPass123!"
TOTAL_USERS = 120
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123456"


def seed_users(client: httpx.Client, count: int = TOTAL_USERS):
    """Register N test users. Ignores duplicates if they already exist."""
    created = 0
    for i in range(count):
        username = f"{TEST_USER_PREFIX}_{i}"
        resp = client.post("/api/auth/register", json={
            "username": username,
            "password": TEST_USER_PASSWORD,
            "email": f"{username}@test.local",
        })
        if resp.status_code == 200:
            created += 1
        elif resp.status_code == 409:
            pass  # Already exists
        else:
            print(f"  WARN: register {username} -> {resp.status_code} {resp.text[:100]}")
        if (i + 1) % 30 == 0:
            print(f"  ... {i + 1}/{count} users processed ({created} new)")
    print(f"  Users: {created} newly created, {count - created} already existed")


def seed_documents(client: httpx.Client, admin_token: str):
    """Upload synthetic e-commerce product documents as admin."""
    test_files = [
        ("product_headphones.txt", """商品名称: 无线蓝牙耳机 Pro Max
价格: 299元
颜色: 黑色、白色、蓝色
材质: ABS工程塑料 + 硅胶耳塞
重量: 45g
电池续航: 8小时连续播放
充电时间: 1.5小时充满
保修期: 1年
特点: 主动降噪、IPX5防水、蓝牙5.3、触摸控制
适用场景: 运动、通勤、办公
包装清单: 耳机×1、充电仓×1、耳塞×3对、USB-C充电线×1、说明书×1"""),
        ("product_watch.txt", """商品名称: 智能运动手表 S3
价格: 899元
颜色: 午夜黑、星光银、远峰蓝
材质: 铝合金表壳 + 氟橡胶表带
屏幕: 1.43英寸 AMOLED
电池续航: 14天典型使用
防水等级: 5ATM（50米防水）
功能: 心率监测、血氧检测、睡眠分析、GPS定位、NFC支付
保修期: 2年
适用人群: 运动爱好者、商务人士
包装清单: 手表×1、磁吸充电器×1、说明书×1"""),
        ("product_shirt.txt", """商品名称: 免烫商务衬衫
价格: 199元
颜色: 白色、浅蓝、深灰、粉色
材质: 新疆长绒棉 + 3%氨纶
尺码: S/M/L/XL/XXL（标准版型，建议按正常尺码选购）
重量: 约280g
特点: 免烫抗皱、吸湿排汗、挺括有型
适用季节: 四季通用
适用场景: 商务会议、日常通勤、婚礼宴会
洗涤建议: 机洗温度不超过40°C，不可漂白，低温熨烫
包装清单: 衬衫×1、备用纽扣×2"""),
        ("product_size_guide.txt", """商品名称: 尺码推荐指南

上衣尺码对照表:
S码: 胸围88-92cm, 肩宽42-44cm, 衣长66-68cm, 建议身高160-168cm, 体重45-55kg
M码: 胸围96-100cm, 肩宽44-46cm, 衣长68-70cm, 建议身高168-175cm, 体重55-68kg
L码: 胸围104-108cm, 肩宽46-48cm, 衣长70-72cm, 建议身高173-180cm, 体重68-80kg
XL码: 胸围112-116cm, 肩宽48-50cm, 衣长72-74cm, 建议身高178-185cm, 体重80-93kg
XXL码: 胸围120-124cm, 肩宽50-52cm, 衣长74-76cm, 建议身高183-190cm, 体重93-108kg

测量方法:
1. 胸围: 自然站立，用软尺水平测量胸部最丰满处
2. 肩宽: 从左肩点到右肩点的直线距离
3. 衣长: 从后领口到衣服下摆的长度

注意事项:
- 如果胸围和肩宽在两个尺码之间，建议选大一号
- 宽松款式可以选择大一号，修身款式按正常尺码选择
- 以上数据为手工测量，可能存在1-2cm误差"""),
        ("product_washing_care.txt", """商品名称: 织物洗护指南

通用洗涤建议:
1. 深色衣物首次穿着前请单独清洗（可能轻微褪色）
2. 不同颜色的衣物请分开洗涤
3. 请勿长时间浸泡（建议不超过30分钟）
4. 洗后请立即晾晒，避免潮湿堆放产生异味

按材质分类的洗护方法:
- 纯棉: 机洗温度30-40°C，可烘干（低温），可熨烫（中温）
- 羊毛: 建议手洗或干洗，水温不超过30°C，不可烘干，低温熨烫
- 真丝: 必须干洗或中性洗涤剂手洗，不可拧绞，不可暴晒
- 化纤: 机洗温度不超过40°C，不可高温烘干，可低温熨烫
- 牛仔: 翻面洗涤减少褪色，水温不超过30°C，自然晾干

常见污渍处理:
- 油渍: 洗涤剂直接涂抹于污渍处，静置5分钟后正常洗涤
- 血渍: 冷水浸泡，用肥皂搓洗（不可用热水）
- 咖啡/茶渍: 立即用温水冲洗，再用洗涤剂搓洗
- 口红/粉底: 用卸妆油或酒精轻擦，再正常洗涤

收纳建议:
- 换季衣物洗净晾干后再收纳
- 使用防潮剂防止霉变
- 西装/大衣建议使用宽肩衣架悬挂
- 针织衣物建议折叠收纳，避免悬挂变形"""),
    ]

    uploaded = 0
    for filename, content in test_files:
        resp = client.post(
            "/api/knowledge/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": (filename, content.encode("utf-8"), "text/plain")},
            timeout=60,
        )
        if resp.status_code in (200, 201):
            uploaded += 1
            print(f"  Uploaded: {filename}")
        else:
            print(f"  FAIL: {filename} -> {resp.status_code} {resp.text[:200]}")
    print(f"  Documents: {uploaded}/{len(test_files)} uploaded")


def main():
    print(f"Seeding stress test data to {TARGET_HOST}...")
    print()

    with httpx.Client(base_url=TARGET_HOST) as client:
        # Step 1: Login as admin
        print("[1/2] Logging in as admin...")
        resp = client.post("/api/auth/login", json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
        })
        if resp.status_code != 200:
            print(f"  FAIL: Admin login returned {resp.status_code}: {resp.text}")
            sys.exit(1)
        admin_token = resp.json()["access_token"]
        print("  OK")

        # Step 2: Seed users
        print(f"[2/3] Seeding {TOTAL_USERS} test users...")
        seed_users(client, TOTAL_USERS)

        # Step 3: Seed documents
        print("[3/3] Uploading test documents...")
        seed_documents(client, admin_token)

    print()
    print("Seed complete! Ready for stress testing.")


if __name__ == "__main__":
    main()
