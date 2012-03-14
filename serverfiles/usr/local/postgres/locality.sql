CREATE OR REPLACE FUNCTION getLocality(int) RETURNS type6bigint AS $$
/* IN:  n_id
 * OUT: portion of local traffic of this node (percent*100)
 */
    DECLARE
        pk          intval%ROWTYPE;
        pid         intval%ROWTYPE;
        downOut     bigint := 0;
        downIn      bigint := 0;
        upOut       bigint := 0;
        upIn        bigint := 0;
        upRes       bigint;
        downRes     bigint;
        xmit        perfcache%ROWTYPE;
        res         type6bigint%ROWTYPE;
    BEGIN
        SELECT pk_id INTO pk FROM perfkeys WHERE pk_name='xmit_data' ORDER BY pk_id LIMIT 1;
        ---- DOWNWARDS
        --RAISE NOTICE 'DOWNWARDS';
        -- Der Verkehr, der zu mir hoch kommt
        FOR pid IN SELECT dst from links join ports on links.src=ports.p_id where n_id=$1 LOOP
        --FOR pid IN SELECT p_id FROM systems NATURAL JOIN nodes NATURAL JOIN ports WHERE uplink AND dlid=$1 LOOP
            SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
            --RAISE NOTICE 'DLID:% PID:% XmitD +:%',$1,pid.val,xmit.pc_val;
            downIn = downIn + xmit.pc_val; 
        END LOOP;
        -- Der Verkehr, den ich wieder nach unten schiebe
        FOR pid IN SELECT src from links join ports on links.src=ports.p_id where n_id=$1 LOOP
        --FOR pid IN SELECT p_id FROM systems NATURAL JOIN nodes NATURAL JOIN ports WHERE NOT uplink AND lid=$1 LOOP
            SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
            --RAISE NOTICE 'LID:% PID:% XmitD -:%',$1,pid.val,xmit.pc_val;
            downOut = downOut + xmit.pc_val; 
        END LOOP;
        ---- UPWARDS
        --RAISE NOTICE 'UPWARDS';
        -- Der Verkehr von mir nach oben
        FOR pid IN SELECT dst from links join ports on links.dst=ports.p_id where n_id=$1 LOOP
        --FOR pid IN SELECT p_id FROM systems NATURAL JOIN nodes NATURAL JOIN ports WHERE uplink AND lid=$1 LOOP
            SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
            --RAISE NOTICE 'LID:% PID:% XmitD +:%',$1,pid.val,xmit.pc_val;
            upOut = upOut + xmit.pc_val; 
        END LOOP;
        -- Der Verkehr zu mir von oben
        FOR pid IN SELECT src from links join ports on links.dst=ports.p_id where n_id=$1 LOOP
        --FOR pid IN SELECT p_id FROM systems NATURAL JOIN nodes NATURAL JOIN ports WHERE not uplink AND dlid=$1 LOOP
            SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
            --RAISE NOTICE 'DLID:% PID:% XmitD -:%',$1,pid.val,xmit.pc_val;
            upIn = upIn + xmit.pc_val; 
        END LOOP;
        IF downOut!=0 THEN
            downRes = (upIn*100)/downOut;
        ELSE
            IF upIn!=0 THEN
                downRes = 100;
            ELSE
                downRes = 0;
            END IF;
        END IF;
        IF downIn!=0 THEN
            upRes = (upOut*100)/downIn;
        ELSE
            IF upOut!=0 THEN
                upRes = 100;
            ELSE
                upRes = 0;
            END IF;
        END IF;
        
        --RAISE NOTICE 'upIn/downOut: %*100/% = %',upIn,downOut,downRes;
        --RAISE NOTICE 'upOut/downIn: %*100/% = %',upOut,downIn,upRes;
        
        --(up,down,upIn,downOut,upOut,downIn)
        SELECT downRes,upRes,upIn,downOut,upOut,downIn INTO res;
        
        RETURN res;
    END;
$$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION getLocality(text) RETURNS type6bigint AS $$
/* IN:  n_id
 * OUT: portion of local traffic of this node (percent*100)
 */
    DECLARE
        node        nodes%ROWTYPE;
        nodetype    nodetypes%ROWTYPE;
        pk          intval%ROWTYPE;
        pid         intval%ROWTYPE;
        downOut     bigint := 0;
        downIn      bigint := 0;
        upOut       bigint := 0;
        upIn        bigint := 0;
        upRes       bigint;
        downRes     bigint;
        xmit        perfcache%ROWTYPE;
        res         type6bigint%ROWTYPE;
    BEGIN
        SELECT * INTO node FROM nodes WHERE n_name=$1;
        SELECT * INTO nodetype FROM nodetypes WHERE nt_id=node.nt_id;
        
        SELECT pk_id INTO pk FROM perfkeys WHERE pk_name='xmit_data' ORDER BY pk_id LIMIT 1;
        IF nodetype.nt_name NOT IN ('root') THEN
            ---- DOWNWARDS
            --RAISE NOTICE 'DOWNWARDS';
            -- Der Verkehr, der zu mir hoch kommt
            FOR pid IN SELECT dst FROM links JOIN ports ON links.src=ports.p_id WHERE n_id=node.n_id LOOP
                SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
                downIn = downIn + xmit.pc_val; 
            END LOOP;
            -- Der Verkehr, den ich wieder nach unten schiebe
            FOR pid IN SELECT src from links join ports on links.src=ports.p_id WHERE n_id=node.n_id LOOP
                SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
                downOut = downOut + xmit.pc_val; 
            END LOOP;
            ---- UPWARDS
            -- Der Verkehr von mir nach oben
            FOR pid IN SELECT dst from links join ports on links.dst=ports.p_id WHERE n_id=node.n_id LOOP
                SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
                --RAISE NOTICE 'LID:% PID:% XmitD +:%',$1,pid.val,xmit.pc_val;
                upOut = upOut + xmit.pc_val; 
            END LOOP;
            -- Der Verkehr zu mir von oben
            FOR pid IN SELECT src from links join ports on links.dst=ports.p_id WHERE n_id=node.n_id LOOP
                SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
                --RAISE NOTICE 'DLID:% PID:% XmitD -:%',$1,pid.val,xmit.pc_val;
                upIn = upIn + xmit.pc_val; 
            END LOOP;
        ELSE
            -- If the node is a root switch the direction is 'interswitch' instead of 'upwards'
            -- because there is no upwards for root...
            ---- NODETRAFFIC (LEAFS)
            -- Traffic generated by leafs
            FOR pid IN SELECT dst
                            FROM links l, ports p1, ports p2,
                                 nodes n, nodetypes nt
                            WHERE l.src=p1.p_id AND
                                  l.dst=p2.p_id AND 
                                  p2.n_id=n.n_id AND
                                  n.nt_id=nt.nt_id AND
                                  nt_name!='switch' AND
                                  p1.n_id=node.n_id
                            LOOP
                SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
                downIn = downIn + xmit.pc_val; 
            END LOOP;
            -- Traffic consumes by leafs
            FOR pid IN SELECT src
                            FROM links l, ports p1, ports p2,
                                 nodes n, nodetypes nt
                            WHERE l.src=p1.p_id AND
                                  l.dst=p2.p_id AND 
                                  p2.n_id=n.n_id AND
                                  n.nt_id=nt.nt_id AND
                                  nt_name!='switch' AND
                                  p1.n_id=node.n_id
                            LOOP
                SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
                downOut = downOut + xmit.pc_val; 
            END LOOP;
            -- Traffic generated by switches
            FOR pid IN SELECT dst
                            FROM links l, ports p1, ports p2,
                                 nodes n, nodetypes nt
                            WHERE l.src=p1.p_id AND
                                  l.dst=p2.p_id AND 
                                  p2.n_id=n.n_id AND
                                  n.nt_id=nt.nt_id AND
                                  nt_name!='switch' AND
                                  p1.n_id=node.n_id
                            LOOP
                SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
                upIn = upOut + xmit.pc_val; 
            END LOOP;
            -- Traffic consumed by switches
            FOR pid IN SELECT dst
                            FROM links l, ports p1, ports p2,
                                 nodes n, nodetypes nt
                            WHERE l.src=p1.p_id AND
                                  l.dst=p2.p_id AND 
                                  p2.n_id=n.n_id AND
                                  n.nt_id=nt.nt_id AND
                                  nt_name!='switch' AND
                                  p1.n_id=node.n_id
                            LOOP
                SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
                upout = upIn + xmit.pc_val; 
            END LOOP;
            
        END IF;
        IF downOut!=0 THEN
            downRes = (upIn*100)/downOut;
        ELSE
            IF upIn!=0 THEN
                downRes = 100;
            ELSE
                downRes = 0;
            END IF;
        END IF;
        IF downIn!=0 THEN
            upRes = (upOut*100)/downIn;
        ELSE
            IF upOut!=0 THEN
                upRes = 100;
            ELSE
                upRes = 0;
            END IF;
        END IF;
        
        
        --(up,down,upIn,downOut,upOut,downIn)
        SELECT downRes,upRes,upIn,downOut,upOut,downIn INTO res;
        
        RETURN res;
    END;
$$ LANGUAGE 'plpgsql';

