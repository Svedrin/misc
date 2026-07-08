import java.sql.*;
import java.util.*;

/**
 * Migrates an HSQLDB 2.6.x file-based database to MariaDB/MySQL.
 *
 * Compile:
 *   javac -cp /usr/share/java/hsqldb-2.6.0.jar:/usr/share/java/mariadb-java-client.jar HsqlToMariaDB.java
 *
 * Run:
 *   java -cp .:/usr/share/java/hsqldb-2.6.0.jar:/usr/share/java/mariadb-java-client.jar HsqlToMariaDB
 */
public class HsqlToMariaDB {

    // ── Source: HSQLDB ────────────────────────────────────────────────────────
    static final String HSQL_URL  = "jdbc:hsqldb:file:/home/path/to/my/Database;readonly=true";
    static final String HSQL_USER = "SA";
    static final String HSQL_PASS = "";

    // ── Target: MariaDB/MySQL ─────────────────────────────────────────────────
    static final String MYSQL_HOST = "localhost";   // ← change me
    static final int    MYSQL_PORT = 3306;
    static final String MYSQL_DB   = "dbaseuser";   // ← change me (must already exist)
    static final String MYSQL_USER = "dbaseuser";   // ← change me
    static final String MYSQL_PASS = "secretpwd";   // ← change me

    // Tables to exclude from the migration (empty = migrate everything)
    static final Set<String> SKIP_TABLES = new HashSet<>(Arrays.asList(
        // "SOME_TABLE_I_DONT_WANT"
    ));

    // ─────────────────────────────────────────────────────────────────────────

    public static void main(String[] args) throws Exception {
        String mysqlUrl = "jdbc:mariadb://" + MYSQL_HOST + ":" + MYSQL_PORT
                + "/" + MYSQL_DB + "?useUnicode=true&characterEncoding=UTF-8"
                + "&allowMultiQueries=true&rewriteBatchedStatements=true";

        try (Connection src = DriverManager.getConnection(HSQL_URL, HSQL_USER, HSQL_PASS);
             Connection dst = DriverManager.getConnection(mysqlUrl, MYSQL_USER, MYSQL_PASS)) {

            dst.setAutoCommit(false);

            List<String> tables = listTables(src);
            System.out.println("Found " + tables.size() + " tables: " + tables);

            try (Statement st = dst.createStatement()) {
                st.execute("SET FOREIGN_KEY_CHECKS=0");
                st.execute("SET NAMES utf8mb4");
            }
            dst.commit();

            System.out.println("\n── Dropping existing tables ──────────────────────────");
            // Drop in reverse order to avoid FK issues even though checks are off
            List<String> reversed = new ArrayList<>(tables);
            Collections.reverse(reversed);
            for (String table : reversed) {
                try (Statement st = dst.createStatement()) {
                    st.execute("DROP TABLE IF EXISTS `" + table + "`");
                    System.out.println("  Dropped: " + table);
                }
            }
            dst.commit();

            System.out.println("\n── Creating tables ───────────────────────────────────");
            for (String table : tables) {
                createTable(src, dst, table);
            }
            dst.commit();

            System.out.println("\n── Copying data ──────────────────────────────────────");
            for (String table : tables) {
                copyData(src, dst, table);
            }

            try (Statement st = dst.createStatement()) {
                st.execute("SET FOREIGN_KEY_CHECKS=1");
            }
            dst.commit();

            System.out.println("\nDone.");
        }
    }

    // ── Schema introspection ──────────────────────────────────────────────────

    static List<String> listTables(Connection src) throws SQLException {
        List<String> tables = new ArrayList<>();
        DatabaseMetaData meta = src.getMetaData();
        try (ResultSet rs = meta.getTables(null, "PUBLIC", "%", new String[]{"TABLE"})) {
            while (rs.next()) {
                String name = rs.getString("TABLE_NAME");
                if (!SKIP_TABLES.contains(name)) {
                    tables.add(name);
                }
            }
        }
        return tables;
    }

    static void createTable(Connection src, Connection dst, String table) throws Exception {
        DatabaseMetaData meta = src.getMetaData();

        // Columns
        List<String> colDefs = new ArrayList<>();
        try (ResultSet cols = meta.getColumns(null, "PUBLIC", table, "%")) {
            while (cols.next()) {
                String col    = cols.getString("COLUMN_NAME");
                int    type   = cols.getInt("DATA_TYPE");
                String tname  = cols.getString("TYPE_NAME");
                int    size   = cols.getInt("COLUMN_SIZE");
                int    dec    = cols.getInt("DECIMAL_DIGITS");
                boolean noNull = cols.getInt("NULLABLE") == DatabaseMetaData.columnNoNulls;
                String  dflt  = cols.getString("COLUMN_DEF");
                boolean autoInc = "YES".equalsIgnoreCase(cols.getString("IS_AUTOINCREMENT"));

                StringBuilder def = new StringBuilder("`").append(col).append("` ")
                        .append(toMysqlType(type, tname, size, dec));

                if (noNull)   def.append(" NOT NULL");
                if (autoInc)  def.append(" AUTO_INCREMENT");
                // Propagate simple boolean defaults
                if (dflt != null && !autoInc) {
                    if (dflt.equalsIgnoreCase("FALSE") || dflt.equals("0")) {
                        def.append(" DEFAULT 0");
                    } else if (dflt.equalsIgnoreCase("TRUE") || dflt.equals("1")) {
                        def.append(" DEFAULT 1");
                    }
                }

                colDefs.add(def.toString());
            }
        }

        // Primary key
        List<String> pkCols = new ArrayList<>();
        try (ResultSet pks = meta.getPrimaryKeys(null, "PUBLIC", table)) {
            Map<Integer, String> ordered = new TreeMap<>();
            while (pks.next()) {
                ordered.put(pks.getInt("KEY_SEQ"), pks.getString("COLUMN_NAME"));
            }
            pkCols.addAll(ordered.values());
        }

        StringBuilder sql = new StringBuilder("CREATE TABLE `").append(table).append("` (");
        sql.append(String.join(", ", colDefs));
        if (!pkCols.isEmpty()) {
            sql.append(", PRIMARY KEY (");
            for (int i = 0; i < pkCols.size(); i++) {
                if (i > 0) sql.append(", ");
                sql.append("`").append(pkCols.get(i)).append("`");
            }
            sql.append(")");
        }
        sql.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");

        try (Statement st = dst.createStatement()) {
            st.execute(sql.toString());
        }
        System.out.println("  Created: " + table + " (" + colDefs.size() + " columns)");
    }

    // ── Type mapping ──────────────────────────────────────────────────────────

    static String toMysqlType(int jdbcType, String hsqlName, int size, int dec) {
        switch (jdbcType) {
            case Types.BIGINT:    return "BIGINT";
            case Types.INTEGER:   return "INT";
            case Types.SMALLINT:  return "SMALLINT";
            case Types.TINYINT:   return "TINYINT";
            case Types.BOOLEAN:
            case Types.BIT:       return "TINYINT(1)";
            case Types.DOUBLE:
            case Types.FLOAT:     return "DOUBLE";
            case Types.REAL:      return "FLOAT";
            case Types.DECIMAL:
            case Types.NUMERIC:   return dec > 0 ? "DECIMAL(" + size + "," + dec + ")" : "DECIMAL(" + size + ")";
            case Types.DATE:      return "DATE";
            case Types.TIME:      return "TIME";
            case Types.TIMESTAMP: return "DATETIME(6)";
            case Types.VARCHAR:
            case Types.NVARCHAR:  return "VARCHAR(" + Math.min(size, 16383) + ")";
            case Types.CHAR:
            case Types.NCHAR:     return "CHAR(" + Math.min(size, 255) + ")";
            case Types.CLOB:
            case Types.NCLOB:
            case Types.LONGVARCHAR:
            case Types.LONGNVARCHAR: return "LONGTEXT";
            case Types.BLOB:
            case Types.BINARY:
            case Types.VARBINARY:
            case Types.LONGVARBINARY: return "LONGBLOB";
            default:
                System.err.println("  WARNING: unknown JDBC type " + jdbcType + " (" + hsqlName + "), using TEXT");
                return "TEXT";
        }
    }

    // ── Data copy ─────────────────────────────────────────────────────────────

    static void copyData(Connection src, Connection dst, String table) throws Exception {
        String selectSql = "SELECT * FROM \"PUBLIC\".\"" + table + "\"";

        try (Statement st = src.createStatement();
             ResultSet rs  = st.executeQuery(selectSql)) {

            ResultSetMetaData rsMeta = rs.getMetaData();
            int colCount = rsMeta.getColumnCount();

            // Build INSERT with named columns to be safe against ordering differences
            StringBuilder ins = new StringBuilder("INSERT INTO `").append(table).append("` (");
            for (int i = 1; i <= colCount; i++) {
                if (i > 1) ins.append(",");
                ins.append("`").append(rsMeta.getColumnName(i)).append("`");
            }
            ins.append(") VALUES (");
            for (int i = 1; i <= colCount; i++) {
                if (i > 1) ins.append(",");
                ins.append("?");
            }
            ins.append(")");

            int count = 0;
            try (PreparedStatement pst = dst.prepareStatement(ins.toString())) {
                while (rs.next()) {
                    for (int i = 1; i <= colCount; i++) {
                        setParam(pst, i, rs, rsMeta.getColumnType(i));
                    }
                    pst.addBatch();
                    count++;
                    if (count % 200 == 0) {
                        pst.executeBatch();
                        dst.commit();
                        System.out.print("  " + table + ": " + count + " rows\r");
                    }
                }
                pst.executeBatch();
                dst.commit();
            }
            System.out.println("  Copied:  " + table + " — " + count + " rows");
        }
    }

    static void setParam(PreparedStatement pst, int i, ResultSet rs, int colType)
            throws SQLException {
        switch (colType) {
            case Types.CLOB:
            case Types.NCLOB:
            case Types.LONGVARCHAR:
            case Types.LONGNVARCHAR: {
                Clob clob = rs.getClob(i);
                if (clob == null) { pst.setNull(i, Types.VARCHAR); }
                else              { pst.setString(i, clob.getSubString(1, (int) clob.length())); }
                break;
            }
            case Types.BLOB:
            case Types.LONGVARBINARY:
            case Types.VARBINARY:
            case Types.BINARY: {
                Blob blob = rs.getBlob(i);
                if (blob == null) { pst.setNull(i, Types.BLOB); }
                else              { pst.setBytes(i, blob.getBytes(1, (int) blob.length())); }
                break;
            }
            case Types.BOOLEAN:
            case Types.BIT: {
                boolean v = rs.getBoolean(i);
                if (rs.wasNull()) { pst.setNull(i, Types.INTEGER); }
                else              { pst.setInt(i, v ? 1 : 0); }
                break;
            }
            default: {
                Object obj = rs.getObject(i);
                if (obj == null) { pst.setNull(i, colType); }
                else             { pst.setObject(i, obj); }
                break;
            }
        }
    }
}
