# 03 · 切格 / 去背 / 加字

## 一、切格：3.5% 内缩不是万能值，要先量

九宫格里通常有细白分隔线。直接按 `宽/3` 切，会把线切进图里，成品边缘就多一条灰边。

```python
cw, ch = sheet.width // 3, sheet.height // 3
inset = int(min(cw, ch) * 0.035)          # 先按 3.5% 起步
cell = sheet.crop((x0 + inset, y0 + inset,
                   x0 + cw - inset, y0 + ch - inset))
```

**为什么要先量**：3.5% 是多数情况下的经验值，但有的图分隔线更粗、有的格子里角色已经贴边。

- 内缩太少 → 灰线进来
- 内缩太多 → 角色被切掉（往外扩还会让 crop 越界，补黑边）

出完做一次边缘检查：**数最外一圈的不透明像素**。满一圈 = 有边框；零星几点 = 正常。

## 二、去背：必须"四边连通泛洪"

### ❌ 不要这样做

```python
# 全局按颜色删白——会连角色内部的白一起删
pixels[i] = (0,0,0,0) if near_white(p) else pixels[i]
```

白肚皮、白袜子、白眼球、白围裙，全都会变成窟窿。这一条踩过，重做了 24 张。

### ✅ 正确做法

从图像四条边出发，只删"和边界连通的近白像素"：

```python
from collections import deque

def cutout(im, tol=18):
    """从四边连通泛洪去背，保留角色内部的白色。"""
    px = im.load()
    w, h = im.size
    seen = [[False]*w for _ in range(h)]
    q = deque()

    def near_white(p):
        r, g, b = p[:3]
        return r > 255-tol and g > 255-tol and b > 255-tol

    for x in range(w):
        for y in (0, h-1):
            if not seen[y][x] and near_white(px[x, y]):
                seen[y][x] = True; q.append((x, y))
    for y in range(h):
        for x in (0, w-1):
            if not seen[y][x] and near_white(px[x, y]):
                seen[y][x] = True; q.append((x, y))

    while q:
        x, y = q.popleft()
        px[x, y] = (0, 0, 0, 0)
        for dx, dy in ((1,0), (-1,0), (0,1), (0,-1)):
            nx, ny = x+dx, y+dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and near_white(px[nx, ny]):
                seen[ny][nx] = True; q.append((nx, ny))
    return im
```

**tol 取 15–25**：太小留一圈白边，太大会把浅色配饰吃掉。

去完还要修：残留白边、半透明灰边（把边缘 alpha 拉满或直接收缩 1px）。

## 三、加字

| 项 | 规定 |
|---|---|
| 字体 | 站酷快乐体（ZCOOL KuaiLe，SIL OFL 1.1，免费商用）；或思源黑体 |
| 字号 | 格子的 12%–16%，**≤6 字** |
| 位置 | 底部居中，距底边 8%；文字区高度约占格子 35% |
| 颜色 | 白字 + 1–2px 深色描边（或深字 + 白描边），保证任何背景都看得清 |
| 安全区 | 文字离左右边各留 6%，不许压到角色脸 |

**换字体必须连生成器一起换**。只换产物、不换脚本，下一批又会出旧字体——这坑踩过。

## 四、命名与目录

```
主图/01.png … 24.png      # 补零两位，否则平台按 1,10,11,2 排序
缩略图/01.png … 24.png
```

补零这一条没有例外。
