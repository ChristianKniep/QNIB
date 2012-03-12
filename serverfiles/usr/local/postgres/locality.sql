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
        FOR pid IN SELECT dst from links join ports on links.src=ports.p_id natural join nodes where n_name=$1 LOOP
        --FOR pid IN SELECT p_id FROM systems NATURAL JOIN nodes NATURAL JOIN ports WHERE uplink AND dlid=$1 LOOP
            SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
            --RAISE NOTICE 'DLID:% PID:% XmitD +:%',$1,pid.val,xmit.pc_val;
            downIn = downIn + xmit.pc_val; 
        END LOOP;
        -- Der Verkehr, den ich wieder nach unten schiebe
        FOR pid IN SELECT src from links join ports on links.src=ports.p_id natural join nodes where n_name=$1 LOOP
        --FOR pid IN SELECT p_id FROM systems NATURAL JOIN nodes NATURAL JOIN ports WHERE NOT uplink AND lid=$1 LOOP
            SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
            --RAISE NOTICE 'LID:% PID:% XmitD -:%',$1,pid.val,xmit.pc_val;
            downOut = downOut + xmit.pc_val; 
        END LOOP;
        ---- UPWARDS
        --RAISE NOTICE 'UPWARDS';
        -- Der Verkehr von mir nach oben
        FOR pid IN SELECT dst from links join ports on links.dst=ports.p_id natural join nodes where n_name=$1 LOOP
        --FOR pid IN SELECT p_id FROM systems NATURAL JOIN nodes NATURAL JOIN ports WHERE uplink AND lid=$1 LOOP
            SELECT * INTO xmit FROM perfcache WHERE p_id=pid.val AND pk_id=pk.val;
            --RAISE NOTICE 'LID:% PID:% XmitD +:%',$1,pid.val,xmit.pc_val;
            upOut = upOut + xmit.pc_val; 
        END LOOP;
        -- Der Verkehr zu mir von oben
        FOR pid IN SELECT src from links join ports on links.dst=ports.p_id natural join nodes where n_name=$1 LOOP
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

