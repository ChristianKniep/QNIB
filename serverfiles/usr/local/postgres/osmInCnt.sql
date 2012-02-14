/* Fuer den perfquery-Agenten die lid und portnummer einer sysimgguid heraussuchen */
CREATE OR REPLACE VIEW getPort  AS 
	SELECT
		p_id,
        p_int,
        n_name,
        nt_name,
        n_guid,
        s_guid,
        s_name
	FROM    systems NATURAL JOIN nodes NATURAL JOIN ports NATURAL JOIN nodetypes
;

CREATE OR REPLACE FUNCTION osmInAllErrCnt(text,int,int,
                    bigint, bigint, bigint, bigint)
                RETURNS VOID AS $$
/* IN:  NodeGUID,PortNr,time_diff since last insert,
 *              symbol_err_cnt,
 *              xmit_discards,
 *              vl15_dropped,
 *              link_downed,
 *              
 * OUT: void
 */
    DECLARE
        pk          intval%ROWTYPE;
        pd          intval%ROWTYPE;
        ports       intval%ROWTYPE;
    BEGIN
        -- Get key informations to insert the key/value pair 
        SELECT p_id INTO ports FROM getport WHERE n_guid=$1 AND p_int=$2;
        
        IF $4>0 THEN
            SELECT pk_id INTO pk FROM perfkeys WHERE pk_name='symbol_err_cnt' ORDER BY pk_id LIMIT 1;
            SELECT pd_id INTO pd FROM perfdata WHERE p_id=ports.val AND pk_id=pk.val;
            IF NOT FOUND THEN
                INSERT INTO perfdata (p_id,pk_id,pdat_val) VALUES (ports.val,pk.val,$4);
            ELSE
                UPDATE perfdata SET pdat_val=$4, pdat_time=NOW() WHERE pd_id=pd.val;
            END IF;
        END IF;
        
        IF $5>0 THEN
            SELECT pk_id INTO pk FROM perfkeys WHERE pk_name='xmit_discards' ORDER BY pk_id LIMIT 1;
            SELECT pd_id INTO pd FROM perfdata WHERE p_id=ports.val AND pk_id=pk.val;
            IF NOT FOUND THEN
                INSERT INTO perfdata (p_id,pk_id,pdat_val) VALUES (ports.val,pk.val,$5);
            ELSE
                UPDATE perfdata SET pdat_val=$5, pdat_time=NOW() WHERE pd_id=pd.val;
            END IF;
        END IF;

        IF $6>0 THEN
            SELECT pk_id INTO pk FROM perfkeys WHERE pk_name='vl15_dropped' ORDER BY pk_id LIMIT 1;
            SELECT pd_id INTO pd FROM perfdata WHERE p_id=ports.val AND pk_id=pk.val;
            IF NOT FOUND THEN
                INSERT INTO perfdata (p_id,pk_id,pdat_val) VALUES (ports.val,pk.val,$6);
            ELSE
                UPDATE perfdata SET pdat_val=$6, pdat_time=NOW() WHERE pd_id=pd.val;
            END IF;
        END IF;

        IF $7>0 THEN
            SELECT pk_id INTO pk FROM perfkeys WHERE pk_name='link_downed' ORDER BY pk_id LIMIT 1;
            SELECT pd_id INTO pd FROM perfdata WHERE p_id=ports.val AND pk_id=pk.val;
            IF NOT FOUND THEN
                INSERT INTO perfdata (p_id,pk_id,pdat_val) VALUES (ports.val,pk.val,$7);
            ELSE
                UPDATE perfdata SET pdat_val=$7, pdat_time=NOW() WHERE pd_id=pd.val;
            END IF;
        END IF;
    END;
$$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION osmInAllPerfCnt(text,int,int,
                    bigint, bigint, bigint, bigint)
                RETURNS VOID AS $$
/* IN:  NodeGUID,PortNr,time_diff since last insert,
 *              xmit_data,
 *              rcv_data,
 *              xmit_pkts,
 *              rcv_pkts
 *              
 * OUT: void
 */
    DECLARE
        pk          intval%ROWTYPE;
        pd         intval%ROWTYPE;
        ports       intval%ROWTYPE;
    BEGIN
        -- Get key informations to insert the key/value pair 
        SELECT p_id INTO ports FROM getport WHERE n_guid=$1 AND p_int=$2 AND nt_name in ('switch');
        
        IF ports.val IS NOT NULL THEN
            SELECT pk_id INTO pk FROM perfkeys WHERE pk_name='xmit_data' ORDER BY pk_id LIMIT 1;
            SELECT pd_id INTO pd FROM perfdata WHERE p_id=ports.val AND pk_id=pk.val;
            IF NOT FOUND THEN
                INSERT INTO perfdata (p_id,pk_id,pdat_val) VALUES (ports.val,pk.val,$4);
            ELSE
                UPDATE perfdata SET pdat_val=$4, pdat_time=NOW() WHERE pd_id=pd.val;
            END IF;
       
            SELECT pk_id INTO pk FROM perfkeys WHERE pk_name='rcv_data' ORDER BY pk_id LIMIT 1;
            SELECT pd_id INTO pd FROM perfdata WHERE p_id=ports.val AND pk_id=pk.val;
            IF NOT FOUND THEN
                INSERT INTO perfdata (p_id,pk_id,pdat_val) VALUES (ports.val,pk.val,$5);
            ELSE
                UPDATE perfdata SET pdat_val=$5, pdat_time=NOW() WHERE pd_id=pd.val;
            END IF;
            
            SELECT pk_id INTO pk FROM perfkeys WHERE pk_name='xmit_pkts' ORDER BY pk_id LIMIT 1;
            SELECT pd_id INTO pd FROM perfdata WHERE p_id=ports.val AND pk_id=pk.val;
            IF NOT FOUND THEN
                INSERT INTO perfdata (p_id,pk_id,pdat_val) VALUES (ports.val,pk.val,$6);
            ELSE
                UPDATE perfdata SET pdat_val=$6,pdat_time=NOW() WHERE pd_id=pd.val;
            END IF;
            
            SELECT pk_id INTO pk FROM perfkeys WHERE pk_name='rcv_pkts' ORDER BY pk_id LIMIT 1;
            SELECT pd_id INTO pd FROM perfdata WHERE p_id=ports.val AND pk_id=pk.val;
            IF NOT FOUND THEN
                INSERT INTO perfdata (p_id,pk_id,pdat_val) VALUES (ports.val,pk.val,$7);
            ELSE
                UPDATE perfdata SET pdat_val=$7,pdat_time=NOW() WHERE pd_id=pd.val;
            END IF;
            
        END IF;
    END;
$$ LANGUAGE 'plpgsql';