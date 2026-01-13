import matplotlib.pyplot as plt
import matplotlib.font_manager as fm


def setup_chinese_font():
    """
    查找并设置一个可用的中文字体，用于matplotlib绘图。
    """
    # 优先查找的字体列表 (Windows, Linux, macOS)
    font_names = [
        "Microsoft YaHei",  # 微软雅黑 (Windows)
        "SimHei",           # 黑体 (Windows)
        "Dengxian",         # 等线 (Windows)
        "Noto Sans CJK SC",  # Noto Sans CJK (Linux/macOS)
        "WenQuanYi Zen Hei",  # 文泉驿正黑 (Linux)
        "Arial Unicode MS",  # (通用)
    ]

    found_font = None
    for font_name in font_names:
        try:
            # 尝试查找字体
            fm.findfont(font_name, fallback_to_default=False)
            found_font = font_name
            # print(f"找到了可用的中文字体: {found_font}")
            break  # 找到后即退出循环
        except:
            continue

    # 设置matplotlib的字体参数
    plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号
    if found_font:
        plt.rcParams['font.sans-serif'] = [found_font]
    else:
        # print("警告：未找到推荐的中文字体，图形中的中文可能无法正常显示。将回退到 'SimHei'。")
        # plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置一个默认的回退选项
        pass
