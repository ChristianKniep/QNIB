CREATE OR REPLACE FUNCTION setLinkCircle(cirId integer, sNid integer, dNid integer)  RETURNS VOID AS $$
/* IN:  circle id, Source n_id, Destination n_id
 * OUT: void
 * DO:  All connection will be bundeled with circle_id
 */
    DECLARE
        link        type1int1bool%ROWTYPE;
        circleX     circles_x%ROWTYPE;
    BEGIN
        FOR link IN SELECT  l.l_id,
                            l.circle
                        FROM links l,ports p1,ports p2
                        WHERE   l.src = p1.p_id AND
                                l.dst=p2.p_id AND
                                ( -- beide Richtungen muessen beruecksichtigt werden
                                    (p1.n_id=sNid AND p2.n_id=dNid) OR
                                    (p1.n_id=dNid AND p2.n_id=sNid)
                                ) LOOP
            IF NOT link.val2 THEN
                UPDATE links SET circle='t' WHERE l_id=link.val1;
                UPDATE nodes SET cir_cnt = cir_cnt + 1 WHERE n_id IN (sNid,dNid);
            END IF;
            SELECT * INTO circleX FROM circles_x WHERE  cir_id=cirId AND l_id=link.val1;
            IF circleX IS NULL THEN
                INSERT INTO circles_x VALUES (cirId,link.val1);
            END IF;
        END LOOP;
    END;
$$ LANGUAGE 'plpgsql';