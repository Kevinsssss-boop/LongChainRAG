# Stress test pool of Chinese e-commerce questions
# These are diverse queries ensuring cache misses (different questions won't collide)

SAMPLE_QUESTIONS = [
    # Pricing questions
    "这件商品的价格是多少？",
    "有没有打折活动？",
    "这个产品和同类产品相比价格怎么样？",
    "满减优惠怎么算？",
    "会员有额外折扣吗？",
    # Product details
    "有没有红色的款式？",
    "这个产品的材质是什么？",
    "尺码偏大还是偏小？",
    "这个商品有多重？",
    "产品的产地是哪里？",
    # After-sales
    "这个产品的保修期是多久？",
    "可以无理由退货吗？",
    "退货运费谁承担？",
    "换货流程怎么走？",
    "收到货发现有质量问题怎么办？",
    # Shipping
    "配送需要多长时间？",
    "支持哪些快递？",
    "可以指定送货时间吗？",
    "偏远地区能送到吗？",
    "海外可以配送吗？",
    # Usage / care
    "这款产品怎么清洗？",
    "使用的时候需要注意什么？",
    "电池能用多久？",
    "充电需要多长时间？",
    "可以和其它产品搭配使用吗？",
    # Comparison / recommendation
    "和其他产品相比有什么优势？",
    "适合什么年龄段的人使用？",
    "送礼的话哪款比较合适？",
    "性价比最高的是哪一款？",
    "新款的改进在哪里？",
    # Edge cases (very short / very long)
    "好在哪？",
    "颜色？",
    "能帮我推荐一款适合夏天使用的产品吗？需要考虑透气性、舒适度和颜色搭配",
    "这个产品的完整参数列表是什么？包括尺寸、重量、材质、颜色、功率、电压等",
]
