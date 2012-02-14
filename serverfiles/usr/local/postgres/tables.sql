CREATE TABLE states (
    state_id SERIAL,
    state_name VARCHAR(5),
    CONSTRAINT states_pk
        PRIMARY KEY (state_id)
);


CREATE TABLE chassis (
    c_id SERIAL,	
    c_guid varchar (32),
    c_nr integer,
    c_name varchar (255),
    --c_state_id INTEGER REFERENCES states(state_id) DEFAULT 1,
    CONSTRAINT chassis_pk
        PRIMARY KEY (c_id)
);

CREATE TABLE systems (
    s_id SERIAL,
    s_rev INTEGER DEFAULT 0,
    s_guid varchar (32),
    s_name varchar (255),
    s_real boolean DEFAULT 't',
    s_state_id INTEGER REFERENCES states(state_id) DEFAULT 1,
    c_id integer DEFAULT 0,
    CONSTRAINT system_pk
        PRIMARY KEY (s_id)
);

CREATE TABLE nodetypes (
    nt_id SERIAL,	
    nt_name varchar (32),
    CONSTRAINT nodetypes_pk
        PRIMARY KEY (nt_id)
);

CREATE TABLE nodes (
    n_id SERIAL,
    n_rev INTEGER DEFAULT 0,
    n_guid varchar (32),
    n_name varchar (255),
    n_real boolean DEFAULT 't',
    n_state_id INTEGER REFERENCES states(state_id) DEFAULT 1,
    s_id integer references systems(s_id) ON DELETE CASCADE,
    nt_id integer references nodetypes(nt_id),
    cir_cnt integer DEFAULT 0,
    sw_cnt integer DEFAULT 0,
    extSw_cnt integer DEFAULT 0,
    comp_cnt integer DEFAULT 0,
    CONSTRAINT node_pk
        PRIMARY KEY (n_id)
);

CREATE TABLE ports (
    p_id SERIAL,	
    n_id integer references nodes(n_id) ON DELETE CASCADE,
    p_guid varchar (32),
    p_lid integer,
    p_int integer,
    p_ext integer,
    p_state_id INTEGER REFERENCES states(state_id) DEFAULT 1,
    CONSTRAINT ports_pk PRIMARY KEY (p_id),
    CONSTRAINT con1     UNIQUE (n_id,p_int)
);

CREATE TABLE port_history (
    ph_id SERIAL,
    p_id INTEGER REFERENCES ports(p_id),
    ph_state_id INTEGER REFERENCES states(state_id),
    ph_time TIMESTAMP DEFAULT now(),
    ph_message varchar(255),
    CONSTRAINT port_history_pk
        PRIMARY KEY (ph_id)
);

CREATE TABLE node_history (
    nh_id SERIAL,
    n_id INTEGER REFERENCES nodes(n_id),
    nh_state_id INTEGER REFERENCES states(state_id),
    nh_time TIMESTAMP DEFAULT now(),
    nh_message varchar(255),
    CONSTRAINT node_history_pk
        PRIMARY KEY (nh_id)
);

CREATE TABLE circles (
    cir_id SERIAL,
    n_id integer, -- Knoten, der es ausgeloest hat
    pathhex varchar(56),
    CONSTRAINT circles_pk PRIMARY KEY (cir_id)
);

CREATE TABLE links (
    l_id SERIAL,
    src integer references ports(p_id) ON DELETE CASCADE,
    dst integer references ports(p_id) ON DELETE CASCADE,
    width integer,
    speed integer,
    uplink boolean DEFAULT 't',
    l_status varchar(3) DEFAULT 'new',
    circle boolean DEFAULT 'f',
    CONSTRAINT width_check CHECK (width in ('1','2','4','12')),
    CONSTRAINT links_pk PRIMARY KEY (src,dst)
);

CREATE TABLE circles_x (
    cir_id integer,	
    l_id integer,
    CONSTRAINT circles_x_pk
        PRIMARY KEY (cir_id,l_id)
);

-- Topology
CREATE TABLE subgraphs (
    sg_id SERIAL PRIMARY KEY,
    sg_name varchar(32)
    );
INSERT INTO subgraphs VALUES ('0','empty');

CREATE TABLE g_edges (
    -- Spine<>Line-Kanten kommen ans Ende des Graphen
    ge_id SERIAL,
    ge_src_gnid INTEGER,
    ge_src varchar(32),
    ge_dst_gnid INTEGER,
    ge_dst varchar(32),
    ge_pos varchar(96),
    in_topo boolean DEFAULT 'f'
    );
CREATE TABLE sg_options (
    sgo_id SERIAL,
    sg_id INTEGER,
    sgo varchar(255)
    );
CREATE TABLE sg_nodes (
    gn_id SERIAL PRIMARY KEY,
    sg_id INTEGER REFERENCES subgraphs(sg_id) ON DELETE CASCADE, --Nodes are connected to subgraph
    s_id INTEGER,
    n_id INTEGER,
    c_id INTEGER DEFAULT 0,
    gn_name varchar(64),
    gn_pos varchar(64),
    gn_shape varchar(64),
    gn_width varchar(64),
    gn_height varchar(64),
    gn_tooltip varchar(128),
    in_topo boolean DEFAULT 'f'
    );
CREATE TABLE sg_edges (
    sge_id SERIAL PRIMARY KEY,
    sg_id INTEGER REFERENCES subgraphs(sg_id) ON DELETE CASCADE, --Nodes are connected to subgraph
    sge_src_gnid INTEGER,
    sge_src varchar(32),
    sge_dst_gnid INTEGER,
    sge_dst varchar(32),
    sge_pos varchar(96),
    in_topo boolean DEFAULT 'f'
    );
-- Perf/Err
CREATE TABLE perfkeys (
    pk_id SERIAL,	
    pk_name varchar (255),
    CONSTRAINT perfkey_pk
        PRIMARY KEY (pk_id)
);

CREATE TABLE perfdata (
    pd_id SERIAL,
    p_id integer references ports(p_id) ON DELETE CASCADE,
    pk_id integer references perfkeys(pk_id),
    pdat_val bigint,
    pdat_time timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT perfdata_pk
        PRIMARY KEY (p_id,pk_id,pdat_time)
);

