/* osmInErrCnt */
CREATE TYPE porttype            as (p_id integer,n_guid text,s_name text,s_nagios boolean,lid int);
CREATE TYPE intval   	        as (val integer);
CREATE TYPE type2int   	        as (val1 integer, val2 integer);
CREATE TYPE type1int   	        as (val1 integer);

/* linkFunctions.sql */
CREATE TYPE type1int1bool       as (val1 integer,val2 boolean);

/* locality */
CREATE TYPE type6bigint         as (val1 bigint,val2 bigint,val3 bigint,val4 bigint,val5 bigint,val6 bigint);