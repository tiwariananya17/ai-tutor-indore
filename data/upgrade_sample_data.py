# One-off upgrade of the FICTIONAL sample tutors in tutors.csv: Classes 1-12, boards, medium, streams.
# Safe to re-run (does nothing if the file already has a 'stream' column). Names/areas/availability are unchanged.
import csv, os, random
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tutors.csv")
rows = list(csv.DictReader(open(P, encoding="utf-8")))
if "stream" in rows[0]: raise SystemExit("already upgraded")
rng = random.Random(11)
SCI = ["Mathematics","Physics","Chemistry","Biology","English","Computer Science"]
COM = ["Accountancy","Business Studies","Economics","Mathematics","English"]
ART = ["History","Political Science","Geography","Economics","Sociology","Psychology","Hindi","English"]
QC = ["M.Com, B.Ed","B.Com, MBA","CA Inter, B.Com","M.Com"]
QA = ["M.A History, B.Ed","M.A Political Science, B.Ed","M.A Economics, B.Ed","M.A Psychology","M.A Geography, B.Ed"]
BOARDS = [["CBSE"],["CBSE","MP Board"],["ICSE"],["MP Board"],["CBSE","ICSE"],["CBSE"]]
senior = [r for r in rows if r["classes"] in ("9-10","1-10","8-10","6-10","5-10")]
rng.shuffle(senior)
sci, com, art = senior[:18], senior[18:26], senior[26:34]
for r in rows:
    r["board"] = ", ".join(rng.choice(BOARDS)); r["stream"] = ""
    r["medium"] = ";".join(["Hindi"] if r["languages"] == "Hindi" else ["English","Hindi"]); r["languages"] = r["medium"]
for grp, pool, st in ((sci, SCI, "Science"), (com, COM, "Commerce"), (art, ART, "Art")):
    for r in grp:
        lo = rng.choice(["9", "11"]) if st != "Science" else rng.choice(["6", "9", "11"])
        r["classes"] = f"{lo}-12"; r["stream"] = "Arts" if st == "Art" else st
        r["subjects"] = ";".join(rng.sample(pool, rng.choice([3, 4])))
        if st == "Commerce": r["qualification"] = rng.choice(QC)
        if st == "Art": r["qualification"] = rng.choice(QA)
        r["experience"] = str(max(3, int(r["experience"]))); r["fee"] = str(int(r["fee"]) + rng.choice([100, 150, 200]))
# a few middle-school tutors reach Class 8 so every class 1-12 has several tutors
for r in rows:
    if r["classes"] == "1-5" and rng.random() < .3: r["classes"] = "1-8"
cols = ["id","name","gender","qualification","experience","subjects","classes","locality","mode","fee","languages","availability","source","board","medium","stream"]
with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows({k: r.get(k, "") for k in cols} for r in rows)
print("upgraded", len(rows), "tutors")
