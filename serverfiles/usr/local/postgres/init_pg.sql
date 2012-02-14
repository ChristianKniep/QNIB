SET client_encoding = 'UTF8';
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

DROP DATABASE "qnib";

CREATE DATABASE "qnib" WITH TEMPLATE = template0 ENCODING = 'UTF8';


ALTER DATABASE "qnib" OWNER TO postgres;

\connect "qnib"


COMMENT ON SCHEMA public IS 'Standard public schema';

CREATE LANGUAGE plpgsql;

\i tables.sql;
\i types.sql
\i init_tabs.sql;
\i osmInCnt.sql;

