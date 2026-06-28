"""
Schema auto-migration module.

On startup, parses init.sql to get the expected schema, compares it against
the actual MySQL tables, and applies non-destructive migrations:
  - Missing tables → CREATE TABLE
  - Missing columns → ALTER TABLE ADD COLUMN

Existing columns are NEVER dropped or altered — this is development-safe:
you can rename/remove columns manually, then update init.sql for future deploys.
"""

import logging
import os
import re
from collections import OrderedDict

import pymysql
import pymysql.cursors
from config import Config

logger = logging.getLogger(__name__)

# Matches a full CREATE TABLE IF NOT EXISTS statement.
# Uses a simple brace-counting approach to capture the full body.
_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+"
    r"(\w+)"                          # table name
    r"\s*\(",                          # opening paren
    re.DOTALL,
)

# Matches a single column definition line like:
#   col_name  TYPE  [NOT NULL] [DEFAULT ...] [COMMENT '...'] [,]
_COL_DEF_RE = re.compile(
    r"^\s*"
    r"(\w+)"                           # column name
    r"\s+"
    r"("
    r"(?:VARCHAR|CHAR)\s*\(\s*\d+\s*\)"       # string types with width
    r"|(?:TEXT|TINYTEXT|MEDIUMTEXT|LONGTEXT)"  # text types (no width)
    r"|(?:DECIMAL|DOUBLE|FLOAT)\s*\(\s*\d+\s*,\s*\d+\s*\)"  # decimal types
    r"|(?:BIGINT|INT|TINYINT|SMALLINT|MEDIUMINT|INTEGER)"   # int types
    r"(?:\s*\(\s*\d+\s*\))?"                                 # optional width
    r"|(?:DATE|DATETIME|TIMESTAMP|TIME|YEAR|ENUM\s*\([^)]*\)|SET\s*\([^)]*\))"  # date/set/enum
    r")"
    r"(?:\s+UNSIGNED)?"                  # optional unsigned
    r"(?:\s+NOT\s+NULL)?"                # optional NOT NULL
    r"(?:\s+NULL)?"                      # optional NULL
    r"(?:\s+AUTO_INCREMENT)?"            # optional auto_increment
    r"(?:\s+DEFAULT\s+"                  # optional DEFAULT
    r"(?:'[^']*'|\"[^\"]*\"|\d+(?:\.\d+)?|CURRENT_TIMESTAMP(?:\s+ON\s+UPDATE\s+CURRENT_TIMESTAMP)?|NULL)"
    r")?"
    r"(?:\s+ON\s+UPDATE\s+CURRENT_TIMESTAMP)?"  # optional ON UPDATE
    r"(?:\s+PRIMARY\s+KEY)?"                    # optional PRIMARY KEY (inline, for id column)
    r"(?:\s+COMMENT\s+'[^']*')?"                # optional COMMENT
    r"\s*,?\s*$",
    re.IGNORECASE,
)

# Matches index/constraint lines (we skip these for column-level migration)
_INDEX_KEY_RE = re.compile(
    r"^\s*(PRIMARY\s+KEY|UNIQUE\s+KEY|INDEX|KEY|FOREIGN\s+KEY|CONSTRAINT)\s",
    re.IGNORECASE,
)

# Matches the ENGINE/CHARSET trailer
_TRAILER_RE = re.compile(
    r"^\s*\)\s*ENGINE\s*=",
    re.IGNORECASE,
)


def _parse_init_sql(path: str) -> OrderedDict[str, str]:
    """Parse init.sql and return {table_name: full CREATE TABLE statement}.

    Each statement is kept exactly as written so it can be replayed verbatim
    for new-table creation.
    """
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    tables = OrderedDict()

    for m in _CREATE_TABLE_RE.finditer(content):
        table_name = m.group(1)
        start = m.start()

        # Find the matching closing paren by counting braces
        depth = 0
        i = m.end() - 1  # start at the opening paren
        while i < len(content):
            ch = content[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    # Find the full statement end (past ENGINE=InnoDB ... )
                    end = content.index(";", i)
                    stmt = content[start:end + 1].strip()
                    tables[table_name] = stmt
                    break
            i += 1

    logger.info("Parsed %d table definitions from init.sql", len(tables))
    return tables


def _parse_column_defs(create_stmt: str) -> OrderedDict[str, str]:
    """Extract column definitions from a CREATE TABLE statement.

    Returns {column_name: full_column_definition_line} ordered as in the DDL.
    """
    # Extract everything between the first ( and the last ) before ENGINE
    body_match = re.search(r"\((.*)\)\s*ENGINE", create_stmt, re.DOTALL)
    if not body_match:
        return OrderedDict()

    body = body_match.group(1)
    columns = OrderedDict()

    for line in body.split("\n"):
        # Skip index/key/constraint lines
        if _INDEX_KEY_RE.match(line):
            continue
        # Skip pure comment lines
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue

        m = _COL_DEF_RE.match(line)
        if m:
            # Reconstruct a clean column definition
            col_name = m.group(1)
            col_type = m.group(2)
            # Grab the rest of the line after column type for modifiers
            rest_start = m.start(2) + len(col_type)
            rest = line[rest_start:].strip().rstrip(",").strip()
            full_def = f"{col_name} {col_type}"
            if rest:
                full_def += " " + rest
            columns[col_name] = full_def

    return columns


def _get_actual_columns(cursor, table_name: str) -> dict[str, str]:
    """Return {column_name: column_type} for an existing table via information_schema."""
    cursor.execute(
        """
        SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
        """,
        (Config.MYSQL_DB, table_name),
    )
    cols = {}
    for row in cursor.fetchall():
        col_type = row["COLUMN_TYPE"]
        if row["IS_NULLABLE"] == "NO":
            col_type += " NOT NULL"
        if row["COLUMN_DEFAULT"] is not None:
            default = row["COLUMN_DEFAULT"]
            if default == "CURRENT_TIMESTAMP":
                col_type += " DEFAULT CURRENT_TIMESTAMP"
                if "on update current_timestamp" in (row.get("EXTRA") or "").lower():
                    col_type += " ON UPDATE CURRENT_TIMESTAMP"
            elif isinstance(default, str):
                col_type += f" DEFAULT '{default}'"
            else:
                col_type += f" DEFAULT {default}"
        if (row.get("EXTRA") or "").lower() == "auto_increment":
            col_type += " AUTO_INCREMENT"
        cols[row["COLUMN_NAME"]] = col_type
    return cols


def _table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
        (Config.MYSQL_DB, table_name),
    )
    row = cursor.fetchone()
    return row["cnt"] > 0 if row else False


def _get_normalized_type(col_def: str) -> str:
    """Normalize a column definition for approximate comparison.

    We strip whitespace variance, lowercase everything, and normalize common
    aliases so we don't attempt to ALTER columns that are functionally identical.
    """
    norm = re.sub(r"\s+", " ", col_def.strip()).lower()
    # Normalize INTEGER → INT, CHARACTER VARYING → VARCHAR etc.
    norm = norm.replace("integer", "int")
    norm = norm.replace("character varying", "varchar")
    norm = norm.replace("character", "char")
    norm = norm.replace("double precision", "double")
    # current_timestamp on update current_timestamp → canonical ordering
    norm = norm.replace("on update current_timestamp", "")
    if "current_timestamp" in norm and "default current_timestamp" in norm:
        norm = re.sub(r"\bon update current_timestamp\b", "", norm).strip()
        # Re-append at end
        parts = norm.rsplit("default current_timestamp", 1)
        norm = parts[0] + "default current_timestamp on update current_timestamp"
    return norm


def run_migration(init_sql_path: str = None) -> bool:
    """Run schema migration: ensure MySQL matches init.sql.

    Args:
        init_sql_path: Path to init.sql. Defaults to <project_root>/init.sql.

    Returns:
        True if migration completed (or was skipped due to DB unavailable),
        False if a migration step failed.
    """
    if init_sql_path is None:
        init_sql_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "init.sql"
        )

    if not os.path.exists(init_sql_path):
        logger.warning("init.sql not found at %s, skipping migration", init_sql_path)
        return True

    expected_tables = _parse_init_sql(init_sql_path)
    if not expected_tables:
        logger.warning("No CREATE TABLE statements found in init.sql")
        return True

    conn = None
    try:
        conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except pymysql.err.OperationalError as e:
        logger.warning("Cannot connect to MySQL (%s), skipping auto-migration", e)
        return True
    except Exception as e:
        logger.warning("Unexpected error connecting to MySQL: %s", e)
        return True

    try:
        with conn.cursor() as cur:
            for table_name, create_stmt in expected_tables.items():
                if _table_exists(cur, table_name):
                    # Table exists — check for missing columns
                    _add_missing_columns(cur, table_name, create_stmt)
                else:
                    # Table doesn't exist — create it
                    _create_table(cur, table_name, create_stmt)
    except Exception:
        logger.exception("Migration failed")
        conn.close()
        return False

    conn.close()
    logger.info("Schema migration completed successfully")
    return True


def _create_table(cursor, table_name: str, create_stmt: str) -> None:
    """Execute a full CREATE TABLE statement for a new table."""
    try:
        cursor.execute(create_stmt)
        logger.info("[MIGRATE] Created table `%s`", table_name)
    except Exception:
        logger.exception("[MIGRATE] Failed to create table `%s`", table_name)
        raise


def _add_missing_columns(cursor, table_name: str, create_stmt: str) -> None:
    """Compare expected vs actual columns and add any that are missing."""
    expected_cols = _parse_column_defs(create_stmt)
    actual_cols = _get_actual_columns(cursor, table_name)

    for col_name, col_def in expected_cols.items():
        if col_name not in actual_cols:
            # Add the missing column
            try:
                # Build ALTER TABLE ... ADD COLUMN
                alter_sql = f"ALTER TABLE `{table_name}` ADD COLUMN {col_def}"
                cursor.execute(alter_sql)
                logger.info(
                    "[MIGRATE] `%s`.`%s` — added missing column (%s)",
                    table_name, col_name, col_def,
                )
            except Exception:
                logger.exception(
                    "[MIGRATE] `%s`.`%s` — failed to add column",
                    table_name, col_name,
                )
                raise
        else:
            # Column exists — compare types loosely and warn if different
            actual_normalized = _get_normalized_type(actual_cols[col_name])
            expected_normalized = _get_normalized_type(col_def)
            if actual_normalized != expected_normalized:
                logger.debug(
                    "[MIGRATE] `%s`.`%s` type differs (not auto-altered). "
                    "Expected: %s | Actual: %s",
                    table_name, col_name, col_def, actual_cols[col_name],
                )
