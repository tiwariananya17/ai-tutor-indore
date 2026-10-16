"""Run from the project folder:  python -m unittest discover -s tests -v
Uses a temporary database; your real tutor.db is never touched."""
import os, sys, tempfile, datetime, unittest
TMP = tempfile.mkdtemp()
os.environ["TUTOR_DB"] = os.path.join(TMP, "test.db"); os.environ["ADMIN_PASSWORD"] = "Test-Admin-Pass-1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend import main as m
from fastapi import HTTPException

def L(role, email, pw): return m.login(m.Login(role=role, email=email, password=pw))["token"]
def code(fn, *a, **k):
    try: fn(*a, **k); return 200
    except HTTPException as e: return e.status_code
def TL(tid=1):
    c = m.db(); return m.claim(m.Claim(tutor_id=m.tcode(tid), code=m.issue_code(c, tid), password="password123", email=f"tutor{tid}@test.local"))["token"]
def PL(): return L("parent", "pp@x.com", "password123")
def monday(): d = datetime.date.today(); return d + datetime.timedelta(days=(0 - d.weekday()) % 7 or 7)
def parent(email, name="Test Parent"):
    return m.signup(m.Sign(role="parent", name=name, email=email, password="password123"))["token"]
def req(tid=1, date=None, time="16:00", **k):
    return m.Req(tutor_id=tid, kind="Demo", cls="8", subject="Mathematics", date=(date or monday()).isoformat(), time=time, **k)

class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c = m.db(); c.execute("update tutors set availability='Mon 15-18' where id=1"); c.commit()
        m.signup(m.Sign(role="parent", name="Test Parent", email="pp@x.com", password="password123"))




    def test_password_hash_salted_and_legacy_upgrade(self):
        self.assertNotEqual(m.hp("x"), m.hp("x")); self.assertTrue(m.vp("x", m.hp("x"))); self.assertFalse(m.vp("y", m.hp("x")))
        c = m.db(); c.execute("insert into users(role,email,pw,name) values('parent','old@x.com',?,'Old')", [m.legacy("oldpass1")]); c.commit()
        L("parent", "old@x.com", "oldpass1"); self.assertTrue(m.db().execute("select pw from users where email='old@x.com'").fetchone()[0].startswith("pbkdf2$"))

    def test_signup_validation_and_xss_sanitised(self):
        self.assertEqual(code(m.signup, m.Sign(role="admin", name="x", email="a@b.co", password="password123")), 400)
        self.assertEqual(code(m.signup, m.Sign(role="parent", name="x", email="a@b.co", password="short")), 400)
        m.signup(m.Sign(role="tutor", name="<script>alert(1)</script>", email="xss@x.com", password="password123", subjects="Mathematics", qualification="<b>x", locality="Rau", board="CBSE", medium="Hindi"))
        row = m.db().execute("select name,qualification from tutors order by id desc limit 1").fetchone()
        self.assertNotIn("<", row[0] + row[1])
    def test_session_expiry(self):
        t = PL(); m.SESS[t]["exp"] = 0
        self.assertEqual(code(m.user, t), 401)
    def test_booking_rules(self):
        p = parent("b1@x.com")
        self.assertEqual(code(m.mk, req(date=datetime.date.today() - datetime.timedelta(days=1)), x_token=p), 400)  # past
        self.assertEqual(code(m.mk, req(time="20:00"), x_token=p), 400)       # outside availability
        self.assertEqual(code(m.mk, m.Req(tutor_id=1, kind="Demo", cls="8", subject="Latin", date=monday().isoformat(), time="16:00"), x_token=p), 400)
        self.assertEqual(code(m.mk, m.Req(tutor_id=999, kind="Demo", cls="8", subject="Mathematics", date=monday().isoformat(), time="16:00"), x_token=p), 404)
        self.assertEqual(code(m.mk, req(), x_token=p), 200)
        self.assertEqual(code(m.mk, req(), x_token=p), 409)                   # duplicate
        self.assertEqual(code(m.mk, req(), x_token=TL(1)), 403)
    def test_status_flow_double_booking_and_cancel(self):
        p1, p2 = parent("s1@x.com", "Same Name"), parent("s2@x.com", "Same Name")
        d = monday() + datetime.timedelta(days=7)
        m.mk(req(date=d, time="15:00"), x_token=p1); m.mk(req(date=d, time="15:30"), x_token=p2)
        ids = [r["id"] for r in m.reqs(x_token=p1)] + [r["id"] for r in m.reqs(x_token=p2)]
        a, b = ids[0], ids[1]; tt = TL(1)
        self.assertEqual(code(m.setst, a, "Accepted", x_token=p1), 403)       # parent cannot accept
        self.assertEqual(code(m.setst, a, "Hacked", x_token=tt), 400)
        self.assertEqual(code(m.setst, a, "Accepted", x_token=tt), 200)
        self.assertEqual(code(m.setst, b, "Accepted", x_token=tt), 409)       # overlapping slot
        self.assertEqual(code(m.setst, a, "Cancelled", x_token=p2), 403)      # same display name, different parent
        self.assertEqual(code(m.setst, a, "Cancelled", x_token=p1), 200)
        self.assertEqual(len(m.reqs(x_token=p1)), 1)                          # parents see only their own
    def test_phone_and_reviews_need_accepted_request_by_that_parent(self):
        tt = TL(1); m.sp(1, m.Prof(bio="Hi", board="CBSE", phone="98765 43210", fee=400), x_token=tt)
        self.assertNotIn("phone", m.tutors()[0])
        p, q = parent("r1@x.com", "Dup"), parent("r2@x.com", "Dup"); d = monday() + datetime.timedelta(days=14)
        self.assertEqual(code(m.contact, 1, x_token=p), 403); self.assertEqual(code(m.pr, 1, m.Rev(stars=5), x_token=p), 403)
        m.mk(req(date=d, time="16:00"), x_token=p); rid = m.reqs(x_token=p)[0]["id"]; m.setst(rid, "Accepted", x_token=tt)
        self.assertEqual(m.contact(1, x_token=p)["phone"], "9876543210")
        self.assertEqual(code(m.contact, 1, x_token=q), 403)
        self.assertEqual(code(m.pr, 1, m.Rev(stars=9, text="<i>great"), x_token=p), 200)
        self.assertEqual(code(m.pr, 1, m.Rev(stars=5), x_token=p), 400)       # one review each
        self.assertEqual([x for x in m.tutors() if x["id"] == 1][0]["rating"], 5.0)
    def test_admin_only_endpoints(self):
        p = parent("ad@x.com")
        for fn, a in ((m.ver, (1,)), (m.cd, ()), (m.imp, (m.Imp(csv_text="name\n"),))): self.assertEqual(code(fn, *a, x_token=p), 403)
        self.assertEqual(code(m.reqs, x_token=p, all=1), 403)
    def test_csv_import_validates_and_never_self_verifies(self):
        ad = L("admin", m.ADMIN_USER, m.ADMIN_PASS)
        csv_text = "name,gender,qualification,experience,subjects,classes,locality,fee,verified,source\nGood Tutor,F,B.Ed,3,Mathematics,6-10,Palasia,400,1,SAMPLE\n<b>Bad</b>,F,B.Ed,3,Mathematics,6-99,Palasia,400,0,x\n"
        r = m.imp(m.Imp(csv_text=csv_text), x_token=ad); self.assertEqual((r["imported"], r["skipped_rows"]), (1, [3])); self.assertTrue(r["codes"][0]["tutor_id"].startswith("TM-T")); self.assertEqual(code(m.claim, m.Claim(tutor_id=r["codes"][0]["tutor_id"], code=r["codes"][0]["code"], password="password123", email="imp@x.com")), 200)
        row = m.db().execute("select verified,source from tutors where name='Good Tutor'").fetchone(); self.assertEqual((row[0], row[1]), (0, "Public listing"))
    def test_ai_parsing_and_explanations(self):
        q = m.parse("Class 10th Maths and bio, ladies tutor near Vijay Nagar under ₹500, 3+ years, weekend evening, CBSE", {})
        self.assertEqual((q["cls"], q["budget"], q["gender"], q["board"], q["min_exp"]), (10, 500, "F", "CBSE", 3))
        self.assertEqual(set(q["subjects"]), {"Mathematics", "Biology"}); self.assertEqual(q["days"], ["Sat", "Sun"]); self.assertEqual(q["after"], 16)
        r = m.ai(m.Chat(message="class 6 science near palasia"))
        self.assertTrue(r["results"]); self.assertTrue(all(x["reasons"] for x in r["results"])); self.assertTrue(all(0 <= x["match"] <= 99 for x in r["results"]))
        self.assertIn("question", m.ai(m.Chat(message="maths tutor")))
        self.assertIn("Classes 1-12", m.ai(m.Chat(message="class 13 maths"))["question"])
    def test_nearby(self):
        r = m.nearby(22.753, 75.894, 5); self.assertEqual(r[0]["locality"] in ("Vijay Nagar", "Scheme 54", "Scheme 78"), True)
        self.assertEqual(code(m.nearby, 28.6, 77.2), 400)
    def test_messages(self):
        p = parent("m1@x.com", "Chatty"); tt = TL(1)
        m.pm(1, m.Msg(text="Hello"), x_token=p); uid = m.gm(1, x_token=tt)[-1]["uid"]
        self.assertEqual(code(m.pm, 1, m.Msg(text="Reply", uid=uid), x_token=tt), 200)
        self.assertEqual(code(m.pm, 2, m.Msg(text="x", uid=uid), x_token=tt), 403)
        self.assertEqual(code(m.pm, 1, m.Msg(text="  "), x_token=p), 400)
    def test_class_11_12_streams_medium_board(self):
        base=dict(role="tutor",password="password123",locality="Vijay Nagar",board="CBSE",medium="Hindi",classes="11-12")
        self.assertEqual(code(m.signup,m.Sign(name="A",email="c1@x.com",subjects="Accountancy",stream="",**base)),400)
        self.assertEqual(code(m.signup,m.Sign(name="A",email="c2@x.com",subjects="Klingon",stream="Commerce",**base)),400)
        self.assertEqual(code(m.signup,m.Sign(name="A",email="c3@x.com",subjects="Accountancy",stream="Commerce",**{**base,"board":"IB"})),400)
        m.signup(m.Sign(name="Commerce Guru",email="c4@x.com",subjects="Accountancy;Economics;Business Studies",stream="Commerce",**base))
        g=[x for x in m.tutors() if x["name"]=="Commerce Guru"][0]
        self.assertEqual((g["class_range"],g["stream"],g["medium"],g["board"]),([11,12],["Commerce"],["Hindi"],"CBSE"))
        q=m.parse("Class 12 commerce accountancy hindi medium CBSE",{})
        self.assertEqual((q["cls"],q["stream"],q["subjects"],q["medium"],q["board"]),(12,"Commerce",["Accountancy"],"Hindi","CBSE"))
        r=m.ai(m.Chat(message="Class 12 commerce accountancy hindi medium CBSE"))["results"]
        top=[x for x in m.tutors() if x["id"]==r[0]["id"]][0]; txt=" ".join(x[1] for x in r[0]["reasons"])
        self.assertTrue("Commerce" in top["stream"] and "Accountancy" in top["subjects"] and top["class_range"][1]==12); self.assertIn("Commerce stream",txt)
        self.assertTrue(all("Accountancy" in x["subjects"] and x["class_range"][1]>=12 for x in m.tutors() if x["id"] in [y["id"] for y in r]))
        tk=L("tutor","c4@x.com","password123")
        self.assertEqual(code(m.sp,g["id"],m.Prof(subjects="Klingon"),x_token=tk),400)
        self.assertEqual(code(m.sp,g["id"],m.Prof(subjects="Economics",classes="9-12",stream="Commerce;Arts",board="CBSE;ICSE",medium="English;Hindi",fee=500),x_token=tk),200)
        self.assertEqual([x for x in m.tutors() if x["id"]==g["id"]][0]["board"],"CBSE, ICSE")
        c=m.catalog(); self.assertIn("Commerce",c["streams"]); self.assertIn("Accountancy",c["subjects"]["Class 11-12 Commerce"])
        p=parent("c5@x.com"); self.assertEqual(code(m.mk,m.Req(tutor_id=g["id"],kind="Demo",cls="5",subject="Economics",date=monday().isoformat(),time="16:00"),x_token=p),400)

    def test_no_predefined_accounts_and_static_admin(self):
        for role, e in (("parent", "parent@demo.com"), ("tutor", "tutor1@demo.com"), ("admin", "demoadmin@demo.com")): self.assertEqual(code(L, role, e, "demo123"), 401)
        self.assertTrue(L("admin", m.ADMIN_USER, m.ADMIN_PASS)); self.assertEqual(code(L, "parent", m.ADMIN_USER, m.ADMIN_PASS), 401)
        self.assertEqual(code(m.signup, m.Sign(role="parent", name="x", email=m.ADMIN_USER + "@x.com", password="short")), 400)
    def test_wrong_password_throttle(self):
        for _ in range(5): self.assertEqual(code(L, "parent", "pp@x.com", "bad"), 401)
        self.assertEqual(code(L, "parent", "pp@x.com", "password123"), 429); m.FAIL.clear()
    def test_prefed_tutor_claim_flow(self):
        c = m.db(); self.assertEqual(m.tcode(5), "TM-T005")
        self.assertEqual(code(L, "tutor", "TM-T005", "anything"), 401)
        self.assertEqual(code(m.claim, m.Claim(tutor_id="TM-T005", code="WRONG-CODE", password="password123", email="t5@x.com")), 400)
        raw = m.issue_code(c, 5)
        self.assertEqual(code(m.claim, m.Claim(tutor_id="TM-T005", code=raw, password="short", email="t5@x.com")), 400)
        r = m.claim(m.Claim(tutor_id="tm-t005", code=raw.lower(), password="password123", email="t5@x.com")); self.assertEqual(r["user"]["tutor_code"], "TM-T005")
        for ident in ("TM-T005", "t5@x.com", "tm-t5"): self.assertTrue(L("tutor", ident, "password123"))
        self.assertEqual(code(m.claim, m.Claim(tutor_id="TM-T005", code=raw, password="password456", email="t5@x.com")), 400)
        m.claim(m.Claim(tutor_id="TM-T005", code=m.issue_code(c, 5), password="newpassword1")); self.assertEqual(code(L, "tutor", "TM-T005", "password123"), 401)
    def test_claim_lockout(self):
        for _ in range(5): code(m.claim, m.Claim(tutor_id="TM-T006", code="NOPE", password="password123", email="t6@x.com"))
        self.assertEqual(code(m.claim, m.Claim(tutor_id="TM-T006", code="NOPE", password="password123", email="t6@x.com")), 429); m.FAIL.clear()
    def test_prefed_tutors_cover_classes_1_to_12(self):
        ts = m.tutors()
        for k in range(1, 13): self.assertGreaterEqual(sum(1 for t in ts if t["class_range"][0] <= k <= t["class_range"][1]), 3, f"class {k}")
        for st in ("Science", "Commerce", "Arts"): self.assertGreaterEqual(sum(1 for t in ts if st in t["stream"]), 3, st)
        for t in ts:
            if t["source"] == "SAMPLE": self.assertTrue(t["board"] and t["medium"], t["name"])
            if t["class_range"][1] >= 11: self.assertTrue(t["stream"], t["name"])
        self.assertTrue(all(t["tutor_code"].startswith("TM-T") for t in ts))
    def test_admin_codes_stats_ics(self):
        ad = L("admin", m.ADMIN_USER, m.ADMIN_PASS); r = m.newcode(7, x_token=ad); self.assertEqual(r["tutor_id"], "TM-T007"); self.assertEqual(len(r["code"]), 11)
        self.assertEqual(code(m.newcode, 7, x_token=PL()), 403); self.assertEqual(code(m.newcode, 999, x_token=ad), 404)
        s = m.astats(x_token=ad); self.assertGreaterEqual(s["tutors"], 56); self.assertIn("claimed", s); self.assertEqual(code(m.astats, x_token=PL()), 403)
        p, q = parent("i1@x.com"), parent("i2@x.com"); tt = TL(1); d = monday() + datetime.timedelta(days=21)
        m.mk(req(date=d, time="16:00"), x_token=p); rid = m.reqs(x_token=p)[0]["id"]
        self.assertEqual(code(m.ics, rid, x_token=p), 404); m.setst(rid, "Accepted", x_token=tt)
        body = m.ics(rid, x_token=p).body.decode(); self.assertIn("BEGIN:VEVENT", body); self.assertIn("DTSTART:" + d.strftime("%Y%m%d") + "T160000", body)
        self.assertEqual(code(m.ics, rid, x_token=tt), 200); self.assertEqual(code(m.ics, rid, x_token=q), 404)
    def test_conversations_and_threads(self):
        p, q, tt = parent("cv1@x.com", "Chat Parent"), parent("cv2@x.com", "Other Parent"), TL(9)
        self.assertEqual(code(m.thread_send, 9, m.Msg(text="  "), x_token=p), 400); self.assertEqual(code(m.thread_send, 999, m.Msg(text="hi"), x_token=p), 404)
        self.assertEqual(m.conv_list(x_token=p), [])
        self.assertEqual(code(m.thread_send, 1, m.Msg(text="cold"), x_token=tt), 403)          # tutors cannot start a chat
        self.assertEqual(code(m.thread_send, 9, m.Msg(text="Hello sir, any slot on Monday?"), x_token=p), 200)
        cp = m.conv_list(x_token=p); self.assertEqual((cp[0]["id"], cp[0]["last"]), (9, "Hello sir, any slot on Monday?"))
        ct = m.conv_list(x_token=tt); self.assertEqual(ct[0]["name"], "Chat Parent"); uid = ct[0]["id"]
        self.assertEqual(code(m.thread_send, uid, m.Msg(text="Yes, 5 PM works."), x_token=tt), 200)
        th = m.thread_get(9, x_token=p); self.assertEqual([x["mine"] for x in th], [True, False]); self.assertEqual(m.thread_get(uid, x_token=tt)[1]["mine"], True); self.assertTrue(th[0]["at"])
        self.assertEqual(m.thread_get(9, x_token=q), []); self.assertEqual(m.conv_list(x_token=q), [])   # other parents see nothing
        self.assertEqual(code(m.thread_get, 9, x_token=L("admin", m.ADMIN_USER, m.ADMIN_PASS)), 403)
        m.thread_send(9, m.Msg(text="Thanks!"), x_token=p); self.assertEqual(m.conv_list(x_token=p)[0]["last"], "Thanks!")
        ad = L("admin", m.ADMIN_USER, m.ADMIN_PASS); cl = m.conv_list(x_token=ad); self.assertTrue(cl and "-" in str(cl[0]["id"]))   # admin sees every conversation, read-only
        tid_, uid_ = str(cl[0]["id"]).split("-"); at = m.admin_thread(int(tid_), int(uid_), x_token=ad); self.assertTrue(at and at[0]["who"])
        self.assertEqual(code(m.admin_thread, int(tid_), int(uid_), x_token=p), 403); self.assertEqual(code(m.admin_thread, int(tid_), int(uid_), x_token=q), 403)
if __name__ == "__main__": unittest.main()
