"""AV 루트 한 장: 위 띠 = 고속도로(남행, 구간 순서만), 아래 = 지역 지도(실제 비율), 오른쪽 = 설명"""
import sys, json, math, warnings
warnings.filterwarnings("ignore")
sys.path.append(r"C:\Program Files (x86)\Eclipse\Sumo\tools")
import sumolib
from PIL import Image, ImageDraw, ImageFont
net = sumolib.net.readNet("skku.net.xml")
R = json.load(open(sys.argv[1], encoding="utf-8"))
f = lambda s: ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", s)
fr = lambda s: ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", s)
x0, x1, y0, y1, S = -1000, 560, -1470, 360, 0.95
W, H, HB, PAD = int((x1 - x0) * S), int((y1 - y0) * S), 360, 720
img = Image.new("RGB", (W + PAD, HB + H), (255, 255, 255)); d = ImageDraw.Draw(img, "RGBA")
T = lambda p: ((p[0] - x0) * S, HB + (y1 - p[1]) * S)
AV, ROAD = (235, 90, 30), (92, 92, 100)
C = {"고속": (45, 45, 50), "신호": (210, 40, 40), "분기": (20, 110, 200), "버스": (0, 150, 90), "오거리": (130, 60, 180),
     "비정형": (200, 120, 0), "회전": (20, 140, 80), "학교": (190, 30, 120), "주차": (90, 90, 90)}


def marker(x, y, t, col, r=16):
    d.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,), outline=(255, 255, 255, 255), width=3)
    fo = f(17 if len(t) < 2 else 14)
    tw = d.textlength(t, font=fo)
    d.text((x - tw / 2, y - (12 if len(t) < 2 else 10)), t, fill="white", font=fo)


def arrows(pts, step=120):
    acc = 0
    for a, b in zip(pts, pts[1:]):
        acc += math.dist(a, b)
        if acc > step:
            acc = 0
            ang = math.atan2(b[1] - a[1], b[0] - a[0]); m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            pt = lambda k, r: (m[0] + math.cos(ang + k) * r, m[1] + math.sin(ang + k) * r)
            d.polygon([pt(0, 10), pt(2.5, 10), pt(-2.5, 10)], fill=(255, 255, 255))


# ── 아래: 지역 지도 ──
d.rectangle([0, HB, W, HB + H], fill=(246, 245, 241))
d.polygon([T(tuple(p)) for p in json.load(open("campus_poly.json"))], fill=(225, 236, 222, 255))
for e in net.getEdges():
    if e.getID().startswith(("hw_", "P")) or not e.allows("passenger"):
        continue
    z = e.getLanes()[0].getShape3D()[0][2]
    col = (92, 100, 178, 220) if z > 3 else (195, 195, 200, 255) if z < -3 else (150, 150, 156, 255)
    d.line([T(p[:2]) for p in e.getShape()], fill=col, width=max(2, int(e.getLaneNumber() * 3.2 * S)), joint="curve")
pts = []
for i in R["local"] + R["campus"] + R["exit"]:
    pts += [T(p[:2]) for p in net.getEdge(i).getShape()]

# ── 위: 고속도로 띠 (남행만, 왼→오른) ──
d.rectangle([0, 0, W, HB], fill=(250, 250, 252))
d.text((24, 14), "고속도로 구간: 봉담과천로 남행 (구간 순서만 맞춘 그림, 약 2.9 km)", fill=(30, 30, 30), font=f(22))
SY, LW = 150, 10
ex, ey = T((28, 355))                          # 서부로가 지도에 들어오는 점
BX, BR = ex - 100, 100                         # 오른쪽 끝에서 아래로 꺾는 곳, 반지름


def bar(xa, xb, n, yc=SY, col=ROAD):
    d.rectangle([xa, yc - n * LW / 2, xb, yc + n * LW / 2], fill=col)
    for k in range(1, n):
        yy = yc - n * LW / 2 + k * LW
        for xx in range(int(xa), int(xb), 14):
            d.line([(xx, yy), (xx + 7, yy)], fill=(230, 230, 230))


bar(24, 120, 3, col=(185, 185, 190)); bar(120, BX, 3)
d.text((24, SY - 36), "← 학의JC·청계IC 방면", fill=(150, 150, 150), font=fr(15))
arc = [(BX + BR * math.sin(t / 20 * math.pi / 2), SY + BR * (1 - math.cos(t / 20 * math.pi / 2))) for t in range(21)]
d.line(arc + [(ex, HB + 6)], fill=ROAD, width=3 * LW, joint="curve")


def accel(xa, xb):                              # 바깥(아래) 4번째 차로, 끝은 비스듬히 줄어듦
    d.polygon([(xa, SY + 15), (xb, SY + 15), (xb - 30, SY + 25), (xa, SY + 25)], fill=ROAD)
    d.line([(xa, SY + 15), (xb - 30, SY + 15)], fill=(230, 160, 40), width=2)


def ramp(xa, ya, xb, yb, col, label, lx):
    d.line([(xa, ya), (xb, yb)], fill=col, width=7)
    d.text((lx, max(ya, yb) + 4), label, fill=col, font=f(16))


G, B = (20, 140, 80), (20, 110, 200)
accel(150, 290); ramp(70, 245, 150, SY + 20, G, "청계IC에서 진입", 20)
ramp(340, SY + 15, 395, 245, B, "휴게소로", 360); ramp(485, 245, 540, SY + 20, G, "휴게소에서 합류", 450); accel(540, 650)
TX = (690, 735, 770, 815)                       # 요금소: 펼침 시작, 부스 앞, 부스 뒤, 다시 3차로
d.polygon([(TX[0], SY - 15), (TX[1], SY - 50), (TX[2], SY - 50), (TX[3], SY - 15),
           (TX[3], SY + 15), (TX[2], SY + 50), (TX[1], SY + 50), (TX[0], SY + 15)], fill=ROAD)
for k in range(1, 10):
    yy = SY - 50 + k * 10
    d.line([(TX[1], yy), (TX[2], yy)], fill=(230, 230, 230))
d.rectangle([TX[1] + 12, SY - 54, TX[2] - 12, SY + 54], fill=(200, 205, 215))
d.text((TX[0] - 30, SY - 88), "의왕TG 요금소", fill=(210, 40, 40), font=f(18))
d.text((TX[0] - 20, SY + 58), "3→10→3차로", fill=(210, 40, 40), font=fr(15))
hpts = [(150, SY)] + [(x, SY) for x in range(160, int(BX), 10)] + arc + [(ex, HB + 6)]
d.line(hpts + pts, fill=AV + (235,), width=9, joint="curve"); arrows(hpts + pts)
marker(150, SY, "H1", C["고속"]); marker(565, SY, "H2", C["고속"]); marker(752, SY, "H3", (210, 40, 40))
d.text((165, SY - 64), "AV 출발", fill=AV, font=f(20))
d.text((24, HB - 62), "고속도로 차는 IDM 추종 (가속 1.0·감속 2.0 m/s², 차간 1.2초), 시간당 약 1,000~1,200대:", fill=(80, 80, 80), font=fr(16))
d.text((24, HB - 38), "합류·요금소의 작은 감속이 뒤로 퍼지는 유령 체증을 볼 수 있게 함 (실제 발생은 아직 측정 전)", fill=(80, 80, 80), font=fr(16))
# 경계: 위는 그림, 아래는 실제 지도
for xx in range(0, W, 18):
    d.line([(xx, HB), (xx + 9, HB)], fill=(170, 170, 170), width=2)
d.text((W - 300, HB + 10), "▼ 여기부터 실제 지도 (서부로)", fill=(110, 110, 110), font=f(16))

P = [(1, (2, -9), "신호 사거리 (성대역)", "고속도로에서 이어진 서부로 남행 대기 줄(정류장 2곳, 버스 정차) 속에서 지상 차로로 미리 맞추기 → 직진 신호(50초)로 통과", "신호"),
     (2, (-10, -40), "분기 · 차로 감소", "고가(2차로)/지상(1차로) 갈림 → 지상 1차로로 미리 차로 바꾸기", "분기"),
     (3, (-55, -160), "버스 · 합류", "지상 서부로 1차로, 성균관대역 정류장 2곳: 정차한 버스 뒤 대기·추월, 골목에서 나오는 차 합류", "버스"),
     (4, (-111, -263), "올리브영 사거리 (G2)", "고가 밑 넓은 신호 교차로(방향별 직좌 신호): 오른쪽 골목(서부로2123번길)으로 우회전, 다른 신호 땐 양보하며", "비정형"),
     (5, (-185, -257), "오거리", "골목 오거리 좌회전", "오거리"),
     (6, (-260, -294), "오거리", "우선순위 없는 골목: 눈치 보며 통과", "오거리"),
     (7, (-311, -288), "오거리", "율전로로 이어짐", "오거리"),
     (8, (-424, -453), "비정형 사거리", "비스듬히 만나는 골목", "비정형"),
     (9, (-553, -540), "회전교차로", "진입 양보 → 율전로64번길로 나감", "회전"),
     (10, (-253, -1084), "신호 사거리 (서부로×일월로)", "아파트 사이 율전로64번길 끝: 1차로 직좌 신호(18초) 차례를 기다려 직진 → 일월로 동쪽", "신호"),
     (11, (127, -1086), "학교 정문", "일월로에서 좌회전해 정문 진입 (마주 오는 차) → 정문 길 따라 Modular Bldg 지나 Global Plaza 앞에서 우회전", "학교"),
     (12, (335, -845), "교내 주차장 (L1)", "여러 줄 통로를 돌며 빈 칸 찾아 주차 → 출차 (주차·출차하는 차와 엇갈림)", "주차"),
     (13, (35, -600), "교내 순환로 (일방통행)", "반시계 방향으로 캠퍼스 한 바퀴: 동쪽 길 → 위쪽 길 → 서쪽 길 → 정문으로", "학교"),
     (14, (185, -1112), "정문 나가며 좌회전", "일월로 동쪽 → 분리 구간 3+3차로 → 오른쪽 아래(일월로 남쪽 끝) 도착", "신호")]
for n, p, kind, desc, c in P:
    q = T(p)
    if n in (12, 13):                           # 교내 표시는 경로 선 위 가장 가까운 점으로
        q = min(pts, key=lambda a: math.dist(a, q))
    marker(*q, str(n), C[c])
x, y = T((474, -1445))
d.rounded_rectangle([x - 44, y - 16, x + 44, y + 16], 8, fill=(30, 30, 30, 230)); d.text((x - 20, y - 13), "도착", fill="white", font=f(18))

# ── 오른쪽 설명 ──
d.rectangle([W, 0, W + PAD, HB + H], fill=(255, 255, 255))   # 지도 밖으로 나간 도로 덮기
d.line([(W, 0), (W, HB + H)], fill=(210, 210, 210), width=2)
X, yy = W + 28, 22
d.text((X, yy), "AV 루트: 고속도로 → 성대역 → 골목", fill=(20, 20, 20), font=f(29)); yy += 42
d.text((X, yy), "→ 학교 주차장·순환로 → 일월로", fill=(20, 20, 20), font=f(29)); yy += 50
d.text((X, yy), "전체 약 7.8 km = 고속도로 2.9 km + 성대역부터 4.9 km", fill=(70, 70, 70), font=f(18)); yy += 26
d.text((X, yy), "정문 진입로(들어갈 때·나올 때)만 빼고 같은 길을 두 번 지나지 않음", fill=(70, 70, 70), font=f(18)); yy += 44


def item(num, kind, desc, col):
    global yy
    marker(X + 16, yy + 15, num, col, r=17)
    d.text((X + 44, yy - 2), kind, fill=col, font=f(22))
    words, line, lines = desc.split(" "), "", []
    for w_ in words:
        if d.textlength(line + " " + w_, font=fr(17)) > PAD - 100:
            lines.append(line); line = w_
        else:
            line = (line + " " + w_).strip()
    lines.append(line)
    for k, ln in enumerate(lines):
        d.text((X + 44, yy + 28 + k * 22), ln, fill=(70, 70, 70), font=fr(17))
    yy += 36 + 22 * len(lines) + 10


item("H1", "청계IC 합류 · AV 출발", "가속 차로(4→3차로): 들어오는 차와 본선 차 사이 끼어들기", C["고속"])
item("H2", "휴게소 합류", "휴게소에서 나온 차가 가속 차로로 끼어듦", C["고속"])
item("H3", "의왕TG 요금소", "3차로 → 부스 10개로 펼침 → 다시 3차로로 번갈아 합류", (210, 40, 40))
yy += 6; d.line([(X, yy), (X + PAD - 60, yy)], fill=(225, 225, 225), width=2); yy += 16
for n, p, kind, desc, c in P:
    item(str(n), kind, desc, C[c])
yy += 4
d.line([(X, yy + 10), (X + 60, yy + 10)], fill=AV, width=9); d.text((X + 72, yy - 2), "AV 루트 (흰 화살표 = 진행 방향)", fill=(50, 50, 50), font=fr(17)); yy += 30
d.line([(X, yy + 10), (X + 60, yy + 10)], fill=(92, 100, 178), width=9); d.text((X + 72, yy - 2), "서부로 고가 / 연두 면 = 캠퍼스", fill=(50, 50, 50), font=fr(17)); yy += 50
shot = Image.open(sys.argv[2]).crop((725, 60, 797, 580)).rotate(90, expand=True)
shot = shot.resize((PAD - 60, int(shot.height * (PAD - 60) / shot.width)))
d.text((X, yy), "SUMO 화면: 의왕TG 요금소 (남행 →, 회색 띠 = 부스 지붕)", fill=(40, 40, 40), font=f(17)); yy += 30
img.paste(shot, (X, yy)); d.rectangle([X, yy, X + shot.width, yy + shot.height], outline=(180, 180, 180), width=2)
print(img.size, "설명 끝", yy + shot.height)
img.save(sys.argv[3])
