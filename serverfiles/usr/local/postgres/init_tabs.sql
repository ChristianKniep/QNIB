/* Nodetypes */
insert into nodetypes (nt_name) VALUES ('host');
insert into nodetypes (nt_name) VALUES ('switch');

/* Chassis */
insert into chassis (c_id,c_name) VALUES ('0','empty');

/* States */
INSERT INTO states (state_name) VALUES ('new');
INSERT INTO states (state_name) VALUES ('chk');
INSERT INTO states (state_name) VALUES ('ok');
INSERT INTO states (state_name) VALUES ('deg');
INSERT INTO states (state_name) VALUES ('nok');