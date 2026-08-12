import pymssql
conn = pymssql.connect('192.111.111.80', 'sa', 'Nuctech_50', 'idr_rdb')
cursor = conn.cursor(as_dict=True)
cursor.execute("SELECT TOP 1 s.TYPEVALUE FROM IDR_CHECK_UNIT cu JOIN IDR_CHECK_SIIG cs ON cs.CHECKUNITID = cu.ID JOIN IDR_SIIG s ON s.ID = cs.SIIGID WHERE s.TYPE = 'inputinfo'")
print(cursor.fetchone())
