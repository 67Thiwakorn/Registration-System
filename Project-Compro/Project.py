import struct, os, datetime

# ===== CONFIG =====
STUDENT_FILE = "students.dat"
COURSE_FILE = "courses.dat"
ENROLL_FILE = "enrollments.dat"
REPORT_FILE = "report.txt"

# Student: ID, Name(50), Year, Major(30)
STU_FMT = "<I50sI30s"
COURSE_FMT = "<I50sI"   # course_id, name(50), credit
ENROLL_FMT = "<III10s"  # enroll_id, student_id, course_id, grade(10)

STU_SIZE = struct.calcsize(STU_FMT)
COURSE_SIZE = struct.calcsize(COURSE_FMT)
ENROLL_SIZE = struct.calcsize(ENROLL_FMT)

# ถ้าไฟล์เก่าเป็น student แบบไม่มี Major ใช้ format นี้
STU_OLD_FMT = "<I50sI"
STU_OLD_SIZE = struct.calcsize(STU_OLD_FMT)

# ===== UTIL =====
def str_to_bytes(s, size): 
    return s.encode()[:size].ljust(size, b"\x00")

def bytes_to_str(b): 
    return b.split(b"\x00",1)[0].decode()

def write_record(file, fmt, rec):
    with open(file,"ab") as f: 
        f.write(struct.pack(fmt,*rec))

def read_all(file, fmt, size):
    """อ่าน record แบบปลอดภัย ข้าม partial chunk"""
    recs=[]
    if not os.path.exists(file): return recs
    with open(file,"rb") as f:
        while True:
            chunk=f.read(size)
            if not chunk: break
            if len(chunk)!=size:
                print(f"Warning: Incomplete record in {file} ({len(chunk)} bytes, expected {size}). Ignored.")
                break
            recs.append(struct.unpack(fmt,chunk))
    return recs

def overwrite_by_key(file, fmt, size, key_index, key_value, new_rec):
    recs = read_all(file, fmt, size)
    with open(file, "r+b") as f:
        for idx, r in enumerate(recs):
            vals = [bytes_to_str(x) if isinstance(x, bytes) else str(x) for x in r]
            if str(vals[key_index]) == str(key_value):
                f.seek(idx*size)
                f.write(struct.pack(fmt, *new_rec))
                return True
    return False


def delete(file, size, index):
    with open(file,"r+b") as f:
        f.seek(index*size)
        f.write(b"\x00"*size)

# ===== Integrity / Migration =====
def check_file_integrity(path, rec_size):
    if not os.path.exists(path): return True
    sz=os.path.getsize(path)
    ok=(sz%rec_size==0)
    if not ok:
        print(f"File '{path}' size {sz} not multiple of {rec_size}.")
    return ok

def trim_file_partial(path, rec_size):
    if not os.path.exists(path): return
    sz=os.path.getsize(path)
    keep=(sz//rec_size)*rec_size
    if keep==sz: return
    bak=path+".bak"
    if not os.path.exists(bak):
        os.replace(path,bak)
        print(f"Backup: {bak}")
    with open(bak,"rb") as fin, open(path,"wb") as fout:
        fout.write(fin.read(keep))
    print(f"Trimmed {path} to {keep} bytes (removed {sz-keep}).")

def migrate_students(old_path, old_fmt, old_size, new_path, new_fmt, default_major="Undeclared"):
    if not os.path.exists(old_path): return
    bak=old_path+".bak_migrate"
    if not os.path.exists(bak):
        os.replace(old_path,bak)
        print(f"Backup original: {bak}")
    migrated=0
    with open(bak,"rb") as fin, open(new_path,"wb") as fout:
        while True:
            chunk=fin.read(old_size)
            if not chunk: break
            if len(chunk)!=old_size: break
            sid,name_b,year=struct.unpack(old_fmt,chunk)
            major_b=default_major.encode()[:30].ljust(30,b'\x00')
            new_rec=(sid,name_b,year,major_b)
            fout.write(struct.pack(new_fmt,*new_rec))
            migrated+=1
    print(f"Migrated {migrated} records to {new_path}")

# ===== CRUD Operations =====
def add_student():
    sid=int(input("Student ID: "))
    name=str_to_bytes(input("Name-Surname: "),50)
    year=int(input("Year: "))
    major=str_to_bytes(input("Major: "),30)
    write_record(STUDENT_FILE,STU_FMT,(sid,name,year,major))

def update_student():
    sid = input("Student ID to update: ").strip()
    recs = read_all(STUDENT_FILE, STU_FMT, STU_SIZE)
    found = False
    for r in recs:
        if str(r[0]) == sid:
            print("Found:", [bytes_to_str(x) if isinstance(x, bytes) else x for x in r])
            new_sid = int(input("New Student ID: "))
            new_name = str_to_bytes(input("New Name: "),50)
            new_year = int(input("New Year: "))
            new_major = str_to_bytes(input("New Major: "),30)
            if overwrite_by_key(STUDENT_FILE, STU_FMT, STU_SIZE, 0, sid, (new_sid,new_name,new_year,new_major)):
                print("Updated.")
            else:
                print("Update failed.")
            found = True
            break
    if not found:
        print("Student not found.")


def delete_student():
    sid = int(input("Student ID to delete: "))
    recs = read_all(STUDENT_FILE, STU_FMT, STU_SIZE)
    found = False
    for idx, r in enumerate(recs):
        if r[0] == sid:
            vals = [bytes_to_str(x) if isinstance(x, bytes) else x for x in r]
            print("Found:", vals)
            confirm = input("Confirm delete this student? (y/n): ")
            if confirm.lower() == "y":
                delete(STUDENT_FILE, STU_SIZE, idx)
                print("Deleted.")
            else:
                print("Cancelled.")
            found = True
            break
    if not found:
        print("Student not found.")


# Course
def add_course():
    cid=int(input("Course ID: "))
    name=str_to_bytes(input("Course Name: "),50)
    credit=int(input("Credit: "))
    write_record(COURSE_FILE,COURSE_FMT,(cid,name,credit))

def update_course():
    cid = input("Course ID to update: ").strip()
    recs = read_all(COURSE_FILE, COURSE_FMT, COURSE_SIZE)
    found = False
    for r in recs:
        if str(r[0]) == cid:
            print("Found:", [bytes_to_str(x) if isinstance(x, bytes) else x for x in r])
            new_cid = int(input("New Course ID: "))
            new_name = str_to_bytes(input("New Course Name: "),50)
            new_credit = int(input("New Credit: "))
            if overwrite_by_key(COURSE_FILE, COURSE_FMT, COURSE_SIZE, 0, cid, (new_cid,new_name,new_credit)):
                print("Updated.")
            else:
                print("Update failed.")
            found = True
            break
    if not found:
        print("Course not found.")

def delete_course():
    cid = int(input("Course ID to delete: "))
    recs = read_all(COURSE_FILE, COURSE_FMT, COURSE_SIZE)
    found = False
    for idx, r in enumerate(recs):
        if r[0] == cid:
            vals = [bytes_to_str(x) if isinstance(x, bytes) else x for x in r]
            print("Found:", vals)
            confirm = input("Confirm delete this course? (y/n): ")
            if confirm.lower() == "y":
                delete(COURSE_FILE, COURSE_SIZE, idx)
                print("Deleted.")
            else:
                print("Cancelled.")
            found = True
            break
    if not found:
        print("Course not found.")


# Enrollment
def add_enroll():
    eid=int(input("Enroll ID: "))
    sid=int(input("Student ID: "))
    cid=int(input("Course ID: "))
    grade=str_to_bytes(input("Grade: "),10)
    write_record(ENROLL_FILE,ENROLL_FMT,(eid,sid,cid,grade))

def update_enroll():
    eid = input("Enroll ID to update: ").strip()
    recs = read_all(ENROLL_FILE, ENROLL_FMT, ENROLL_SIZE)
    found = False
    for r in recs:
        if str(r[0]) == eid:
            print("Found:", [bytes_to_str(x) if isinstance(x, bytes) else x for x in r])
            new_eid = int(input("New Enroll ID: "))
            new_sid = int(input("New Student ID: "))
            new_cid = int(input("New Course ID: "))
            new_grade = str_to_bytes(input("New Grade: "),10)
            if overwrite_by_key(ENROLL_FILE, ENROLL_FMT, ENROLL_SIZE, 0, eid, (new_eid,new_sid,new_cid,new_grade)):
                print("Updated.")
            else:
                print("Update failed.")
            found = True
            break
    if not found:
        print("Enrollment not found.")


def delete_enroll():
    eid = int(input("Enroll ID to delete: "))
    recs = read_all(ENROLL_FILE, ENROLL_FMT, ENROLL_SIZE)
    found = False
    for idx, r in enumerate(recs):
        if r[0] == eid:
            vals = [bytes_to_str(x) if isinstance(x, bytes) else x for x in r]
            print("Found:", vals)
            confirm = input("Confirm delete this enrollment? (y/n): ")
            if confirm.lower() == "y":
                delete(ENROLL_FILE, ENROLL_SIZE, idx)
                print("Deleted.")
            else:
                print("Cancelled.")
            found = True
            break
    if not found:
        print("Enrollment not found.")


# ===== View =====
def view_single(file, fmt, size, labels, key_index=0):
    """View single record by Primary Key (not index)"""
    key = input(f"Enter {labels[key_index]}: ").strip()
    recs = read_all(file, fmt, size)
    found = False
    for r in recs:
        vals = [bytes_to_str(x) if isinstance(x, bytes) else str(x) for x in r]
        if str(vals[key_index]) == key:
            print(" | ".join(f"{labels[j]}={vals[j]}" for j in range(len(vals))))
            found = True
            break
    if not found:
        print("Record not found.")


def view_all(file, fmt, size, labels):
    recs=read_all(file,fmt,size)
    for i,r in enumerate(recs):
        vals=[bytes_to_str(x) if isinstance(x,bytes) else x for x in r]
        print(f"[{i}] "+" | ".join(f"{labels[j]}={vals[j]}" for j in range(len(vals))))

def view_filter(file, fmt, size, labels, field_idx):
    key = input("Filter keyword: ").strip().lower()
    matches = []
    for i, r in enumerate(read_all(file, fmt, size)):
        vals = [bytes_to_str(x) if isinstance(x, bytes) else str(x) for x in r]
        target = str(vals[field_idx]).lower()
        if key in target:  # partial match
            matches.append((i, vals))
    if not matches:
        print("No matches found.")
    else:
        for i, vals in matches:
            print(f"[{i}] " + " | ".join(f"{labels[j]}={vals[j]}" for j in range(len(vals))))


def view_summary():
    stus=read_all(STUDENT_FILE,STU_FMT,STU_SIZE)
    crs=read_all(COURSE_FILE,COURSE_FMT,COURSE_SIZE)
    ens=read_all(ENROLL_FILE,ENROLL_FMT,ENROLL_SIZE)
    print(f"Students={len(stus)}, Courses={len(crs)}, Enrollments={len(ens)}")

# ===== Report =====
def generate_report():
    stus = read_all(STUDENT_FILE, STU_FMT, STU_SIZE)
    crs = read_all(COURSE_FILE, COURSE_FMT, COURSE_SIZE)
    ens = read_all(ENROLL_FILE, ENROLL_FMT, ENROLL_SIZE)

    # Convert students, courses to dict for easy lookup
    students = {
        s[0]: {
            "id": s[0],
            "name": bytes_to_str(s[1]),
            "year": s[2],
            "major": bytes_to_str(s[3]),
        } for s in stus if s[0] != 0
    }
    courses = {
        c[0]: {
            "id": c[0],
            "name": bytes_to_str(c[1]),
            "credit": c[2],
        } for c in crs if c[0] != 0
    }

    # Build enrollments list
    enrollments = []
    for e in ens:
        if e[0] == 0: continue
        enrollments.append({
            "enroll_id": e[0],
            "student_id": e[1],
            "course_id": e[2],
            "grade": bytes_to_str(e[3])
        })

    enrollments = sorted(enrollments, key=lambda x: x["student_id"])

    # ===== Report lines =====
    lines = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S (+07:00)")

    lines.append("Registration System – Summary Report (Sample)")
    lines.append(f"Generated At : {now}")
    lines.append("App Version  : 1.0")
    lines.append("Endianness   : Little-Endian")
    lines.append("Encoding     : UTF-8 (fixed-length)")
    lines.append("")

    header = "+----------+--------------------+------------------------+------+----------+-------------------------------+--------+-------+----------+"
    lines.append(header)
    lines.append("| StudentID| Full Name          | Major                  | Year | CourseID | Course Name                   | Credit | Grade | Status   |")
    lines.append(header)

    last_sid = None
    stats = {"total": 0, "active": 0, "dropped": 0}
    grade_count = {}

    for e in enrollments:
        s = students.get(e["student_id"], {})
        c = courses.get(e["course_id"], {})
        status = "Dropped" if e["grade"] == "W" else "Active"

        stats["total"] += 1
        if status == "Dropped":
            stats["dropped"] += 1
        else:
            stats["active"] += 1
            grade_count[e["grade"]] = grade_count.get(e["grade"], 0) + 1

        if e["student_id"] == last_sid:
            sid, name, major, year = "", "", "", ""
        else:
            sid = str(s.get("id", ""))
            name = s.get("name", "")
            major = s.get("major", "")
            year = str(s.get("year", ""))
        
        line = f"| {sid:<8} | {name:<18} | {major:<22} | {year:<4} | {c.get('id',''):<8} | {c.get('name',''):<29} | {c.get('credit',''):<6} | {e['grade']:<5} | {status:<8} |"
        lines.append(line)
        last_sid = e["student_id"]

    lines.append(header)
    lines.append("")

    # ===== Summary =====
    lines.append("Summary (Active only)")
    lines.append(f"- Total Students    : {len(students)}")
    lines.append(f"- Total Courses     : {len(courses)}")
    lines.append(f"- Total Enrollments : {stats['total']}")
    lines.append(f"- Dropped Records   : {stats['dropped']}")
    lines.append(f"- Active Records    : {stats['active']}")
    lines.append("")

    lines.append("Statistics (Grade, Active only)")
    for g, count in grade_count.items():
        lines.append(f"- {g} count : {count}")
    lines.append("")

    major_count = {}
    for s in students.values():
        major_count[s["major"]] = major_count.get(s["major"], 0) + 1
    lines.append("Students by Major (Active only)")
    for m, cnt in major_count.items():
        lines.append(f"- {m} : {cnt}")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Report generated -> {REPORT_FILE}")

def init_sample_data():
    print("Initializing sample data (overwrite files)...")

    # Students
    sample_students = [
        (1001, str_to_bytes("Somchai Dee",50), 1, str_to_bytes("Computer Science",30)),
        (1002, str_to_bytes("Anong Sookjai",50), 2, str_to_bytes("Information Technology",30)),
        (1003, str_to_bytes("Janpen Rungruang",50), 3, str_to_bytes("Computer Science",30)),
        (1004, str_to_bytes("Krit Prompong",50), 1, str_to_bytes("Software Engineering",30)),
        (1005, str_to_bytes("Suda Chaiyasit",50), 4, str_to_bytes("Information Technology",30)),
    ]
    with open(STUDENT_FILE,"wb") as f:
        for s in sample_students:
            f.write(struct.pack(STU_FMT,*s))

    # Courses
    sample_courses = [
        (2001, str_to_bytes("Computer Programming (Python)",50), 3),
        (2002, str_to_bytes("Data Structures",50), 3),
        (2003, str_to_bytes("Database Systems",50), 3),
        (2004, str_to_bytes("Operating Systems",50), 3),
    ]
    with open(COURSE_FILE,"wb") as f:
        for c in sample_courses:
            f.write(struct.pack(COURSE_FMT,*c))

    # Enrollments
    sample_enrollments = [
        (30001, 1001, 2001, str_to_bytes("A",10)),
        (30002, 1001, 2002, str_to_bytes("B+",10)),
        (30003, 1002, 2003, str_to_bytes("C",10)),
        (30004, 1003, 2001, str_to_bytes("W",10)),
        (30005, 1004, 2002, str_to_bytes("A",10)),
        (30006, 1005, 2004, str_to_bytes("B",10)),
    ]
    with open(ENROLL_FILE,"wb") as f:
        for e in sample_enrollments:
            f.write(struct.pack(ENROLL_FMT,*e))

    print("Sample data written successfully.")


# ===== Main Menu =====
def main():
    # เช็คความสมบูรณ์ของไฟล์ students.dat
    init_sample_data()

    if not check_file_integrity(STUDENT_FILE, STU_SIZE):
        print("Students file not aligned. Run trim or migrate as needed.")

    while True:
        print("\n--- MAIN MENU ---")
        print("1) Add")
        print("2) Update")
        print("3) Delete")
        print("4) View")
        print("5) Generate Report")
        print("0) Exit")
        c=input("Choice: ")
        if c=="1":
            print("1) Student  2) Course  3) Enrollment")
            sub=input("Choice: ")
            if sub=="1": add_student()
            elif sub=="2": add_course()
            elif sub=="3": add_enroll()
        elif c=="2":
            print("1) Student  2) Course  3) Enrollment")
            sub=input("Choice: ")
            if sub=="1": update_student()
            elif sub=="2": update_course()
            elif sub=="3": update_enroll()
        elif c=="3":
            print("1) Student  2) Course  3) Enrollment")
            sub=input("Choice: ")
            if sub=="1": delete_student()
            elif sub=="2": delete_course()
            elif sub=="3": delete_enroll()
        elif c=="4":
            print("1) Student  2) Course  3) Enrollment  4) Summary")
            sub=input("Choice: ")
            if sub=="1":
                print("1) Single  2) All  3) Filter")
                v=input("Choice: ")
                if v=="1": view_single(STUDENT_FILE,STU_FMT,STU_SIZE,["ID","Name","Year","Major"])
                elif v=="2": view_all(STUDENT_FILE,STU_FMT,STU_SIZE,["ID","Name","Year","Major"])
                elif v=="3": view_filter(STUDENT_FILE,STU_FMT,STU_SIZE,["ID","Name","Year","Major"],0)
            elif sub=="2":
                print("1) Single  2) All  3) Filter")
                v=input("Choice: ")
                if v=="1": view_single(COURSE_FILE,COURSE_FMT,COURSE_SIZE,["ID","Name","Credit"])
                elif v=="2": view_all(COURSE_FILE,COURSE_FMT,COURSE_SIZE,["ID","Name","Credit"])
                elif v=="3": view_filter(COURSE_FILE,COURSE_FMT,COURSE_SIZE,["ID","Name","Credit"],0)
            elif sub=="3":
                print("1) Single  2) All  3) Filter")
                v=input("Choice: ")
                if v=="1": view_single(ENROLL_FILE,ENROLL_FMT,ENROLL_SIZE,["EID","StuID","CourseID","Grade"])
                elif v=="2": view_all(ENROLL_FILE,ENROLL_FMT,ENROLL_SIZE,["EID","StuID","CourseID","Grade"])
                elif v=="3": view_filter(ENROLL_FILE,ENROLL_FMT,ENROLL_SIZE,["EID","StuID","CourseID","Grade"],0)
            elif sub=="4":
                view_summary()
        elif c=="5":
            generate_report()
        elif c=="0":
            break

if __name__=="__main__":
    main()
