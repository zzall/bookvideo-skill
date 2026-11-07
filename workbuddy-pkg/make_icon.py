# -*- coding: utf-8 -*-
"""生成 512x512 的 bookvideo 市场图标（无字体依赖，纯几何绘制）。"""
import os
from PIL import Image, ImageDraw

W = H = 512
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 深墨绿圆角底
d.rounded_rectangle([0, 0, W - 1, H - 1], radius=112, fill=(22, 38, 34, 255))
# 内描边
d.rounded_rectangle([22, 22, W - 23, H - 23], radius=92,
                    outline=(255, 255, 255, 30), width=2)
# 顶部柔光
d.ellipse([-60, -230, W + 60, 300], fill=(46, 82, 68, 255))

cx, cy = 256, 330
half_w, half_h = 148, 110
skew = 26

# 左页
d.polygon([(cx - 8, cy - half_h), (cx - half_w, cy - half_h + skew),
           (cx - half_w, cy + half_h + skew - 8), (cx - 8, cy + half_h)],
          fill=(246, 241, 228, 255))
# 右页
d.polygon([(cx + 8, cy - half_h), (cx + half_w, cy - half_h + skew),
           (cx + half_w, cy + half_h + skew - 8), (cx + 8, cy + half_h)],
          fill=(232, 225, 210, 255))
# 书脊
d.line([(cx, cy - half_h + 4), (cx, cy + half_h)], fill=(178, 168, 150, 255), width=7)
# 页面线
for i in range(3):
    y = cy - half_h + 34 + i * 30
    d.line([(cx - 128, y + 10), (cx - 28, y)], fill=(196, 187, 168, 255), width=4)
    d.line([(cx + 28, y), (cx + 128, y + 10)], fill=(196, 187, 168, 255), width=4)

# 播放键：橙色圆 + 白色三角
d.ellipse([cx - 58, cy - 268, cx + 58, cy - 152], fill=(255, 122, 54, 255))
d.polygon([(cx - 14, cy - 238), (cx - 14, cy - 182), (cx + 32, cy - 210)],
          fill=(255, 255, 255, 255))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
img.convert("RGB").save(out, "PNG", optimize=True)
print(out, os.path.getsize(out))
