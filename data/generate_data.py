# Generates 56 FICTIONAL demo tutor profiles (names are made up; NOT real people; source=SAMPLE shows as DEMO in UI). Replace tutors.csv with real public data when available.
import csv, random, os
random.seed(7)
L=["Vijay Nagar","Scheme 54","Scheme 78","Palasia","New Palasia","Bengali Square","Bhawarkuan","Rau","Rajendra Nagar","Saket Nagar","Tilak Nagar","Choithram","AB Road","Sudama Nagar"]
SETS={"1-5":[["Mathematics","English","Hindi","EVS"],["Mathematics","EVS","General Science"],["English","Hindi","EVS"]],
"6-10":[["Mathematics","Science"],["English","Hindi","Social Science"],["Mathematics","Science","English"],["Physics","Chemistry","Science"],["Biology","Science","Chemistry"],["Social Science","Hindi","English"]],
"9-10":[["Mathematics","Science","Physics"],["Mathematics","Physics","Computer Science"],["Chemistry","Biology","Science"],["Mathematics","Science"],["English","Social Science"]],
"1-10":[["Mathematics","Science","English","Hindi"],["English","Hindi","Social Science","Mathematics"]]}
Q=["B.Sc, B.Ed","M.Sc Mathematics, B.Ed","M.Sc Physics, B.Ed","M.Sc Chemistry, B.Ed","M.A English, B.Ed","B.A, B.Ed","B.Com, B.Ed","B.Tech","M.Tech","M.Sc Biology, B.Ed","M.A Hindi, B.Ed","M.Ed","M.Sc Mathematics, Ph.D","Experienced school teacher (B.A)","B.Sc"]
D=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
FN="Priya Anita Neha Kavita Sunita Pooja Ritu Shalini Meera Swati Deepika Nidhi Rekha Seema Anjali Divya Preeti Shweta Komal Richa Sapna Jyoti Radhika Sonal Mamta Archana Varsha Pallavi".split()
MN="Rahul Amit Sandeep Vikram Manish Rajesh Ankit Nitin Sachin Vivek Gaurav Alok Deepak Mohit Suresh Yogesh Ashish Pankaj Harsh Kunal Tarun Mayank Rohit Lalit Naveen Sumit".split()
SN="Sharma Verma Joshi Patel Jain Agrawal Tiwari Mishra Chouhan Rathore Dubey Pandey Saxena Gupta Shukla Soni Mehta Vyas Kulkarni Bhatt".split()
used=set()
def pick(g):
    while True:
        n=random.choice(FN if g=="F" else MN)+" "+random.choice(SN)
        if n not in used: used.add(n); return n
rows=[]
for i in range(1,57):
    g=random.choice('FFM'); nm=pick(g)
    band=random.choice(["1-5","6-10","6-10","9-10","9-10","1-10"]); cls=band if band!="6-10" else random.choice(["6-10","5-10","4-8","8-10"])
    sets=SETS[band if band in SETS else "6-10"]; subs=random.choice(sets); exp=random.randint(1,15)
    fee=min(900,max(200,150+exp*35+random.randint(-60,150))//10*10)
    av=""
    if random.random()>.15:
        days=random.sample(D,random.randint(2,5)); parts=[]
        for d in sorted(days,key=D.index):
            s=random.choice([9,10,15,16,17,18]) if d in("Sat","Sun") else random.choice([15,16,17,18]); parts.append(f"{d} {s}-{min(22,s+random.choice([3,4,5]))}")
        av=";".join(parts)
    rows.append([i,nm,g,random.choice(Q),exp,";".join(subs),cls,random.choice(L),"Home Tuition",fee,";".join(random.choice([["Hindi","English"],["Hindi"],["English","Hindi"]])),av,"SAMPLE"])
w=csv.writer(open(os.path.join(os.path.dirname(__file__),"tutors.csv"),"w",newline="",encoding="utf-8"))
w.writerow("id,name,gender,qualification,experience,subjects,classes,locality,mode,fee,languages,availability,source".split(","));w.writerows(rows)
