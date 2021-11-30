import sqlite3
import csv

app_dict = {}
with open('app_list.csv', newline='') as f:
    row = csv.reader(f, delimiter=',')
    for r in row:
        app_dict[r[5]] = r[3]

conn = sqlite3.connect('review_extend.db')
c = conn.cursor()

# 读取csv，

c.execute('''ALTER TABLE apps ADD COLUMN category''')

# Save (commit) the changes
conn.commit()

for app_id in app_dict:
    print("app_id = {} , app_category = {}".format(app_id, app_dict[app_id]))
    c.execute('''UPDATE apps SET category = ? WHERE name = ?''', [app_dict[app_id], app_id])

print("finish")
conn.commit()
# We can also close the connection if we are done with it.
# Just be sure any changes have been committed or they will be lost.
conn.close()
