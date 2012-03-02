
CREATE OR REPLACE FUNCTION deleteGN(text) RETURNS VOID AS $$
/* IN:  gn_name
 * OUT: void
 * FUNC: Delete all related information of given graph node
 */
    DECLARE
        gn          type2int%ROWTYPE;
        node        type1int%ROWTYPE;
    BEGIN
        -- Get key informations to insert the key/value pair 
        SELECT gn_id,s_id INTO gn FROM sg_nodes WHERE gn_name=$1;
        IF NOT FOUND THEN
            RETURN;
        ELSE
            SELECT n_id INTO node FROM nodes WHERE s_id=gn.val2;
            DELETE FROM node_history WHERE n_id=node.val1;
            DELETE FROM ports WHERE n_id=node.val1;
            DELETE FROM nodes WHERE n_id=node.val1;
            DELETE FROM systems WHERE s_id=gn.val2;
            DELETE FROM sg_nodes WHERE gn_id=gn.val1;
            RETURN;
        END IF;
    END;
$$ LANGUAGE 'plpgsql';

CREATE OR REPLACE VIEW showStates AS
    SELECT
        s2.state_name AS n_status,
        n_name,
        p_int,
        s1.state_name AS p_status
    FROM nodes NATURAL JOIN ports,
         states s1, states s2
    WHERE  p_state_id=s1.state_id AND
           n_state_id=s2.state_id
    ORDER BY n_name
;
