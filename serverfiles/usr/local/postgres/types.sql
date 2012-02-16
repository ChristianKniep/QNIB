/* osmInErrCnt */
CREATE TYPE porttype            as (p_id integer,n_guid text,s_name text,s_nagios boolean,lid int);
CREATE TYPE intval   	        as (val integer);

/* linkFunctions.sql */
CREATE TYPE type1int1bool       as (val1 integer,val2 boolean);