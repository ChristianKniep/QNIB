CREATE OR REPLACE FUNCTION upsert_perf(int, int,bigint,int) RETURNS VOID AS $$
/* IN:  PortID,PerfkeyID,value to insert,timediff to last upsert
 * OUT: void
 */
DECLARE
    typepk  perfkeys%ROWTYPE;
    typepc  perfhist%ROWTYPE;
    txt     type1txt%ROWTYPE;
BEGIN
    SELECT nt_name INTO txt FROM ports NATURAL JOIN nodes NATURAL JOIN nodetypes
                            WHERE p_id=$1;
    SELECT * INTO typepk FROM perfkeys WHERE pk_id=$2;
    IF typepk.pk_name IN ('xmit_wait') THEN
        IF txt.val in ('root','switch','spine') THEN
            SELECT * INTO typepc FROM perfhist WHERE p_id = $1 and pk_id = $2;
            IF NOT FOUND THEN
                INSERT INTO perfhist  (p_id,pk_id,pc_val) VALUES ($1, $2, $3);
                IF $4 != '0' THEN
                    INSERT INTO perfcache (p_id,pk_id,pc_val) VALUES ($1, $2, $3/$4);
                ELSE
                    INSERT INTO perfcache (p_id,pk_id,pc_val) VALUES ($1, $2, $3);
                END IF;
                
            ELSE
                IF typepc.pc_val<$3 THEN
                    IF $4 != '0' THEN
                        PERFORM upsert_perfcache($1, $2, ($3-typepc.pc_val)/$4);
                    ELSE
                        PERFORM upsert_perfcache($1, $2, ($3-typepc.pc_val)/$4);
                    END IF;
                    UPDATE perfhist SET pc_val = $3 WHERE p_id = $1 and pk_id = $2;
                ELSE
                    IF $4 != '0' THEN
                        PERFORM upsert_perfcache($1, $2, $3/$4);
                    ELSE
                        PERFORM upsert_perfcache($1, $2, $3/$4);
                    END IF;
                END IF;
            END IF;
        END IF;
    ELSE    --perfkeys die funktionieren brauchen nicht behandelt werden.
        IF $4 != '0' THEN
            UPDATE perfcache SET pc_val = $3/$4 WHERE p_id = $1 and pk_id = $2;
            IF NOT FOUND THEN
                INSERT INTO perfcache (p_id,pk_id,pc_val) VALUES ($1, $2, $3/$4);
            END IF;
        ELSE
            UPDATE perfcache SET pc_val = $3 WHERE p_id = $1 and pk_id = $2;
            IF NOT FOUND THEN
                INSERT INTO perfcache (p_id,pk_id,pc_val) VALUES ($1, $2, $3);
            END IF;
        END IF;
    END IF;
END;
$$ LANGUAGE 'plpgsql';