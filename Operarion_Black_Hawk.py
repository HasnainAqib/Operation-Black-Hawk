
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math, time, sys, random

# ---------------- Window ----------------
WIN_W, WIN_H = 1280, 800

# ---------------- World -----------------
FOV_Y = 75.0
NEAR_Z, FAR_Z = 0.5, 300000.0   # push far plane for large world
GROUND_EXTENT = 1200000.0        # ~100x the previous 12000
GROUND_STEP   = 600.0            # tile size
GROUND_PATCH_RADIUS_STEPS = 40   # draw (2R+1)^2 tiles around player (~81k tiles max)
PLAY_EXTENT   = 120000.0         # NEW: 10× extent = ~100× area
# --- Ground rendering offsets (to avoid Z-fighting) ---
GROUND_PLANE_Z = 0.0




########################### sealevel stripes
GROUND_LINE_Z  = GROUND_PLANE_Z + 0.05  # stripes/centerlines sit slightly above ground



# ---------------- Flight dynamics ----------------
SPEED_MIN = 120.0
SPEED_MAX = 1200.0
SPEED_STEP = 40.0

# A/D yaw
YAW_RATE_MIN = 10.0     # deg/s @ min speed
YAW_RATE_MAX = 28.0     # deg/s @ max speed

# Pitch
PITCH_RATE   = 30.0     # deg/s

# Q/E bank command (visual)
ROLL_MAX_DEG     = 35.0
ROLL_CMD_RATE    = 90.0
ROLL_TRACK_RATE  = 120.0
ROLL_AUTOCENTER  = 45.0

BANK_DRIFT_RATIO = 0.55

# Flap animations
ELV_MAX = 25.0   # elevon max magnitude (visual)
RUDDER_MAX = 20.0
RUDDER_TRACK = 140.0   # how fast rudder follows the command (deg/s)

# Weapons
BULLET_SPEED = 3000.0
BULLET_LIFE  = 3.8

# ---------------- State ----------------
cam_mode = 'third'            # 'third' or 'first'
orbit_yaw   = 20.0
orbit_pitch = 15.0
cam_dist    = 320.0
cam_height  = 80.0
cam_lock_follow = False

pos       = [0.0, 0.0, 900.0]
yaw_deg   = 0.0
pitch_deg = 0.0
roll_deg  = 0.0          # actual bank
roll_cmd  = 0.0          # target bank (controlled with Q/E)
speed     = 360.0

# yaw input proxy for rudders
rudder_cmd = 0.0   # desired deflection (-RUDDER_MAX .. +RUDDER_MAX)
rudder_deg = 0.0   # actual deflection following rudder_cmd

keys_down = set()
bullets   = []
last_time = None






# --- Player health / cheats ---
PLAYER_HP_MAX = 300
player_hp     = 300
PLAYER_INVINCIBLE = False   # toggle with 'l'

# approximate “radius” for quick sphere-vs-sphere checks vs enemies
PLAYER_SPHERE_R = 70.0




# --- Debug / Hitboxes ---
SHOW_HITBOXES = False   # toggle with 'h' (independent of any other dev flag)

# F-117 oriented hitboxes (half-extents, in world units) + local-center offsets
# tune these 3 numbers later to fit your model snugly
F117_BODY_HALF = (60.0, 12.0, 10.0)   # (forward, right, up) halves
F117_BODY_OFFS = ( 20.0,  0.0,  8.0)  # box center offset from aircraft origin (local space)

F117_WING_HALF = (35.0, 75.0, 2.0)    # thin wide slab for wings
F117_WING_OFFS = (  5.0,  0.0,  0.0)






# --- movement lock (Shift + movement key) ---
MKEYS = {b'q', b'a', b's', b'w', b'd', b'e'}
lock_active     = False
locked_key      = None
lock_candidate  = None




# --- Debug color toggle ---
dev_colors = False   # start in standard mode







# ---------------- Radar / Visibility / Altitude ----------------


# --- Legend overlay (toggle with ';') ---
SHOW_LEGEND = False
LEGEND_W    = 300.0
LEGEND_H    = 360.0
LEGEND_PAD  = 12.0
LEGEND_BG   = (0.0, 0.0, 0.0, 0.65)  # semi-transparent black
legend_anim = {'x': -320.0, 'target': -320.0, 'speed': 900.0, 't_prev': 0.0}

# Small sizes for HUD icons
HUD_SML = 6.0
HUD_MED = 9.0
HUD_THK = 2.0


# --- Radar visual tuning ---
RADAR_TICK_STEPS   = 4          # draw ticks at 1/4, 1/2, 3/4, 1× range
AA_DOT_SIZE        = 4.0
ENEMY_DOT_SIZE     = 5.0
TOWER_DOT_SIZE     = 6.5
MISSILE_DOT_SIZE   = 3.0
BUNKER_DOT_SIZE    = 5.5
BUNKER_AA_HINT_R   = 900.0      # small hint circle around bunkers (visual only)

# cap SAM ring on radar so it never exceeds the panel
def _radar_cap_range(r): 
    return min(r, RADAR_RANGE)



# Visual detection range for gameplay (NOT the camera far plane)
VISUAL_RANGE   = 10000.0          # ≈ 10 km
RADAR_RANGE    = VISUAL_RANGE * 2 # radar shows up to 2× visual (~20 km)

# Radar overlay
RADAR_SIZE     = 180              # px
RADAR_PADDING  = 14               # px from top-right corner
RADAR_ALPHA    = 0.40             # panel translucency

# Player/enemy altitude caps (tune later as needed)
PLAYER_ALT_MIN = 20.0             # keep above ground a bit
PLAYER_ALT_MAX = 4000.0           # ~4 km ceiling for now
ENEMY_ALT_MAX  = 3500.0











# -------- First-person (scope) config --------
FOV_Y_THIRD = FOV_Y        # keep your current 3rd-person FOV as default
FOV_Y_FIRST = 35.0         # narrower, scope-like FOV (tweakable)
SCOPE_VIGNETTE = True
SCOPE_ALPHA = 0.35         # 0..1, how dark the edges feel
RETICLE_SIZE = 14          # pixels
VELVEC_LEN  = 120.0        # length of bullet-direction marker ray (in world units)


AIM_CONE_DEG = 12.0   # fixed aim/“details” cone, independent of missile lock cone



# -------- Compass config --------
COMPASS_TICK = 10          # degrees between tick marks
COMPASS_LABELS = {0: 'N', 90: 'E', 180: 'S', 270: 'W'}

def _wrap360(a):
    a %= 360.0
    return a + 360.0 if a < 0.0 else a

def _heading_deg():
    # 0=N, 90=E, 180=S, 270=W
    # Our yaw_deg increases turning left; convert to compass-style heading
    h = _wrap360(90.0 - yaw_deg)
    return h

#aim assist
GUN_SUREHIT_SLOP = 2.0   # 1.5–2.5 is reasonable; widens sure-hit test slightly


STICK_CONE_EXTRA = 6.0  # degrees of "grace" to keep current target missile while you pan








GLOBAL_POINTERS = False  # toggle with 'p'
# placeholder containers; we’ll fill these when we add ground units / towers
ground_units = []        # [{'p':[x,y,z], 'kind':'sam'|'aa'|'bunker', 'friendly':False, ...}, ...]
towers_of_god = []       # [{'p':[x,y,z], 'friendly':True/False, 'aa': [...]}]
critical_targets = []    # [{'p':[x,y,z]}]  # bunkers etc.











# --- Score ---
score = 0



BULLET_DAMAGE = 5


RAM_DMG_RATE = 20.0  # damage per second while overlapping










# --------- World / Terrain globals ---------
PLAY_EXTENT = 120_000.0      # 250 km half-width
TERRAIN_SEED = 1337
TERRAIN_MAX_H = 1400.0       # mountains peak target
TOWER_COUNT = 7
TOWER_R = 600.0              # “tower of god” cylinder radius
TOWER_H = 12_000.0           # extends way above service ceiling
PLACEMENT_RADIUS = 50_000.0    # ±50 km around tower, radius used for placing content close to tower

AA_SCATTER = 40              # scattered AA guns
SAM_SCATTER = 8              # scattered SAM sites (non-guard)
BUNKER_COUNT = (3, 5)        # min/max bunkers in guarded cluster

# Factions
FACTION_FRIEND = 1
FACTION_FOE    = 2

# Datasets
towers = []       # {p(x,y), r, h, faction, last_hit, loiter_t}
tower_aas = []    # {p(x,y,z), tower_idx}
aa_units = []     # {p(x,y), z_base}
sam_units = []    # {p(x,y), z_base}
bunkers = []      # {p(x,y), z_base, cluster_id}



# --- Lock IDs for ground targets ---
_ground_uid = 1
def _new_gid():
    global _ground_uid
    gid = _ground_uid; _ground_uid += 1
    return gid

def _ground_by_id(gid):
    for lst in (tower_aas, aa_units, sam_units, bunkers):
        for u in lst:
            if u.get('id') == gid:
                return u
    return None


















# ---------- Missiles ----------
FRONT_CONE_DEG = 12.0  # FPS targeting cone
MISSILES = {
    'A2A_S': { # short-range IR
        'name':'A2A-S', 'kind':'IR',
        'lock_cone_deg': 15.0, 'lock_range': 6000.0, 'lock_time': 0.7,
        'speed': 1200.0, 'time': 7.0, 'turn_rate_dps': 35.0,
        'damage': 45, 'aoe': 60.0, 'falloff':'linear', 'hit_r': 8.0, 'model':'arrow'
    },
    'A2A_M': { # medium-range radar
        'name':'A2A-M', 'kind':'RADAR',
        'lock_cone_deg': 25.0, 'lock_range': 12000.0, 'lock_time': 1.2,
        'speed': 1100.0, 'time': 12.0, 'turn_rate_dps': 22.0,
        'damage': 70, 'aoe': 80.0, 'falloff':'shallow', 'hit_r': 10.0, 'model':'arrow'
    },
    'A2S_G': { # air-to-surface (temp allow aircraft)
        'name':'A2S-G', 'kind':'TV',
        'lock_cone_deg': 20.0, 'lock_range': 8000.0, 'lock_time': 1.0,
        'speed': 800.0, 'time': 14.0, 'turn_rate_dps': 12.0,
        'damage': 100, 'aoe': 150.0, 'falloff':'none', 'hit_r': 12.0, 'model':'round'
    },
}

MSL_AMMO = {'A2A_S': 50, 'A2A_M': 50, 'A2S_G': 50}
MSL_SELECTED = 'A2A_S' # default selected missile type


IR_SEEKER_CONE_DEG = 12.0    # IR will switch to a flare inside this cone
FLARE_LIFE = 4.0             # sec (per jet later)
FLARE_W, FLARE_H = 90.0, 60.0
FLARE_COOLDOWN = 6.0         # per-plane later




# Active missile list and fire key
missiles = []               # active missiles in flight
MSL_FIRE_KEY = b'x'         # press 'x' to fire




msl_armed = False     # holding trigger (X/RMB)
last_flare_time = -999.0
flares = []           # active flares





# target/lock state
_target_id = None        # enemy 'id'
_lock_timer = 0.0
_lock_state = 'NONE'     # NONE / ACQ / LOCK






explosions = []  # active explosion FX







# Ground weapons
AA_RANGE_H     = 6_000.0              # AA horizontal reach
TOWER_NOFIRE_R = 5_000.0              # tower "no fire" bubble
TOWER_AA_RANGE = 9_000.0              # tower AA reach (8–10 km nominal)
SAM_RANGE      = 25_000.0             # large ring (2D)
SAM_COOLDOWN   = 20.0                 # one per minute per SAM
AA_COOLDOWN    = 1.2                  # simple cadence
AA_BULLET_SPD  = 850.0
AA_BULLET_LIFE = 6.0
AA_BULLET_DMG  = 8.0

aa_shots = []  # {'p':[x,y,z],'v':[vx,vy,vz],'t0':time,'life':AA_BULLET_LIFE}








# --- Terrain shape controls (mountains + one smooth valley near spawn) ---
TERRAIN_MOUNTAIN_GAIN = 1.0        # >1 = taller mountains
VALLEY_SEED_TH  = random.random()*math.tau  # random valley direction
VALLEY_CENTER   = (0.0, 0.0)                 # through spawn for now
VALLEY_LEN      = 30_000.0                   # half-length along axis (~30 km each way)
VALLEY_WIDTH    = 2_500.0                    # lateral 1-sigma (~2.5 km)
VALLEY_DEPTH    = 900.0                      # carve depth at center (m)






PLAYER_HULL_CLEARANCE = 18.0  # meters to lower the center for ground collision; tweak 12–25


# ---------- SAM unit spawn ----------
def make_sam(x, y, z):
    return {
        'id': _new_gid(),
        'p': [x, y],
        'z': z,
        'hp': 160,
        'hp_max': 160,
        'cool': 0.0,
        'loaded': True,
        'aiming': False
    }






# ---------------- ENEMY SYSTEM ----------------





def _spawn_sam_from(x,y,z):
    spec = {'speed': 1000.0, 'time': 22.0, 'turn_rate_dps': 28.0,
        'damage': 65, 'aoe': 90.0, 'falloff':'linear', 'hit_r': 10.0, 'model':'ammo', 'kind':'RADAR'}
    # head toward player now
    to = _norm3([pos[0]-x, pos[1]-y, pos[2]-z])
    vel = [to[0]*spec['speed'], to[1]*spec['speed'], to[2]*spec['speed']]
    missiles.append({
        'key': 'SAM', 'kind': spec['kind'], 'model': spec['model'],
        'pos': [x,y,z], 'vel': vel, 'speed': spec['speed'],
        'turn_dps': spec['turn_rate_dps'],
        'damage': spec['damage'], 'aoe': spec['aoe'], 'falloff': spec['falloff'],
        'hit_r': spec['hit_r'],
        'time': spec['time'], 'age': 0.0,
        'orig_target_id': None, 'target_id': None,
        'target_flare': None, 'trail': [],
        'target_player': True
    })


# --- SAM logic (loaded/aiming + fire on cooldown) ---
def update_sams(dt):
    for s in sam_units:
        # range + LOS gate
        in_range = (math.hypot(pos[0]-s['p'][0], pos[1]-s['p'][1]) <= SAM_RANGE)
        eye_sam  = [s['p'][0], s['p'][1], s['z'] + 40.0]
            # Slightly looser clearance helps in valleys; keeps terrain masking meaningful
        s['aiming'] = in_range and has_line_of_sight(eye_sam, [pos[0],pos[1],pos[2]], clearance=22.0)



        # cooldown tick
        s['cool'] = s.get('cool', 0.0) - dt

        # auto-reload when cooldown ends
        if s['cool'] <= 0.0 and not s.get('loaded', True):
            s['loaded'] = True

        # fire only if aiming AND loaded AND off cooldown
        if s['aiming'] and s.get('loaded', True) and s['cool'] <= 0.0:
            _spawn_sam_from(s['p'][0], s['p'][1], s['z']+40.0)
            s['cool'] = SAM_COOLDOWN
            s['loaded'] = False








def _spawn_aa_bullet(x,y,z):
    to = _norm3([pos[0]-x, pos[1]-y, pos[2]-z])
    aa_shots.append({'p':[x,y,z], 'v':[to[0]*AA_BULLET_SPD, to[1]*AA_BULLET_SPD, to[2]*AA_BULLET_SPD],
                     't0': time.time(), 'life': AA_BULLET_LIFE})

def update_aa_shots(dt):
    if not aa_shots: return
    keep=[]
    for s in aa_shots:
        s['p'][0]+=s['v'][0]*dt; s['p'][1]+=s['v'][1]*dt; s['p'][2]+=s['v'][2]*dt
        alive = (time.time()-s['t0']) < s['life']
        # hit player?
        if not PLAYER_INVINCIBLE:
            dx= s['p'][0]-pos[0]; dy=s['p'][1]-pos[1]; dz=s['p'][2]-pos[2]
            if (dx*dx+dy*dy+dz*dz) <= (50.0**2):
                player_take_damage(AA_BULLET_DMG, cause="aa")
                spawn_explosion(s['p'], base_radius=40.0, ttl=0.25, kind='generic')
                alive=False
        if alive and s['p'][2]>0.0:
            keep.append(s)
    aa_shots[:] = keep

def draw_aa_shots():
    if not aa_shots: return
    glDisable(GL_LIGHTING)
    glColor3f(1.0,0.4,0.4); glPointSize(5.0)
    glBegin(GL_POINTS)
    for s in aa_shots: glVertex3f(*s['p'])
    glEnd()






def update_ground_weapons(dt):
    # tower AA
    for a in tower_aas:
        t = towers[a['tower_idx']]
        dist = math.hypot(pos[0]-t['p'][0], pos[1]-t['p'][1])
        if t['faction']==FACTION_FOE and dist >= TOWER_NOFIRE_R and dist <= TOWER_AA_RANGE:
            # LOS from AA pod to player
            if has_line_of_sight([a['p'][0],a['p'][1],a['p'][2]], [pos[0],pos[1],pos[2]], clearance=28.0):
                a['cool'] = a.get('cool',0.0) - dt
                if a['cool'] <= 0.0:
                    _spawn_aa_bullet(a['p'][0], a['p'][1], a['p'][2])
                    a['cool'] = AA_COOLDOWN

    # scattered AA
    for u in aa_units:
        d = math.hypot(pos[0]-u['p'][0], pos[1]-u['p'][1])
        if d <= AA_RANGE_H:
            if has_line_of_sight([u['p'][0],u['p'][1],u['z']], [pos[0],pos[1],pos[2]], clearance=28.0):
                u['cool'] = u.get('cool',0.0) - dt
                if u['cool'] <= 0.0:
                    _spawn_aa_bullet(u['p'][0], u['p'][1], u['z'])
                    u['cool'] = AA_COOLDOWN

    # SAM sites handled in update_sams() (already LOS-gated)

















# Shared helper primitives (all axes in local model space; nose points +X)
def _draw_box(hx, hy, hz, rgb=(0.6,0.6,0.6)):
    glColor3f(*rgb)
    # vertices centered at origin
    x0,x1 = -hx, hx; y0,y1 = -hy, hy; z0,z1 = -hz, hz
    glBegin(GL_QUADS)
    # +X / -X
    glVertex3f(x1,y0,z0); glVertex3f(x1,y1,z0); glVertex3f(x1,y1,z1); glVertex3f(x1,y0,z1)
    glVertex3f(x0,y0,z1); glVertex3f(x0,y1,z1); glVertex3f(x0,y1,z0); glVertex3f(x0,y0,z0)
    # +Y / -Y
    glVertex3f(x0,y1,z0); glVertex3f(x1,y1,z0); glVertex3f(x1,y1,z1); glVertex3f(x0,y1,z1)
    glVertex3f(x0,y0,z1); glVertex3f(x1,y0,z1); glVertex3f(x1,y0,z0); glVertex3f(x0,y0,z0)
    # +Z / -Z
    glVertex3f(x0,y0,z1); glVertex3f(x1,y0,z1); glVertex3f(x1,y1,z1); glVertex3f(x0,y1,z1)
    glVertex3f(x0,y1,z0); glVertex3f(x1,y1,z0); glVertex3f(x0,y0,z0); glVertex3f(x0,y0,z0)
    glEnd()

def _draw_cylinder_x(length, radius, slices=14, rgb=(0.65,0.65,0.67)):
    glColor3f(*rgb)
    x0 = -length*0.5; x1 = +length*0.5
    glBegin(GL_TRIANGLE_STRIP)
    for i in range(slices+1):
        th = 2.0*math.pi*i/slices
        c,s = math.cos(th), math.sin(th)
        glVertex3f(x0, radius*c, radius*s)
        glVertex3f(x1, radius*c, radius*s)
    glEnd()
    # caps
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(x0,0,0)
    for i in range(slices+1):
        th = 2.0*math.pi*i/slices
        glVertex3f(x0, radius*math.cos(th), radius*math.sin(th))
    glEnd()
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(x1,0,0)
    for i in range(slices,-1,-1):
        th = 2.0*math.pi*i/slices
        glVertex3f(x1, radius*math.cos(th), radius*math.sin(th))
    glEnd()

def _draw_cylinder_z(height, radius, slices=16, rgb=(0.6,0.6,0.6)):
    """Vertical cylinder (along +Z), base at z=0, height up by `height`."""
    glPushMatrix()
    glTranslatef(0, 0, height*0.5)   # center it so our X-axis helper fits
    glRotatef(90, 0, 1, 0)           # turn X-axis cylinder upright
    _draw_cylinder_x(height, radius, slices=slices, rgb=rgb)
    glPopMatrix()



def _draw_cone_x(length, radius, slices=14, rgb=(0.7,0.7,0.72)):
    glColor3f(*rgb)
    base = -length*0.5; tip = +length*0.5
    # side
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(tip,0,0)
    for i in range(slices+1):
        th = 2.0*math.pi*i/slices
        glVertex3f(base, radius*math.cos(th), radius*math.sin(th))
    glEnd()
    # base cap
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(base,0,0)
    for i in range(slices+1):
        th = 2.0*math.pi*i/slices
        glVertex3f(base, radius*math.cos(th), radius*math.sin(th))
    glEnd()

def _draw_flat_tris(pts, rgb=(0.6,0.6,0.6)):
    glColor3f(*rgb); glBegin(GL_TRIANGLES)
    for a,b,c in pts:
        glVertex3f(*a); glVertex3f(*b); glVertex3f(*c)
    glEnd()

# --- Enemy model builders (extremely low poly; canonical sizes feed hit radii) ---
def build_enemy_A10(pal):
    fus_L, fus_R = 120, 14
    wing_span, wing_chord = 120, 18
    tail_span, tail_chord = 70, 12
    eng_R, eng_L = 10, 30
    _draw_cylinder_x(fus_L, fus_R, rgb=pal['fus'])
    glPushMatrix(); glTranslatef(+fus_L*0.5,0,0); _draw_cone_x(26, fus_R*0.95, rgb=pal['wing']); glPopMatrix()
    glPushMatrix(); glTranslatef(-10, 0, 0); _draw_box(wing_chord*0.5, wing_span*0.5, 1.5, rgb=pal['wing']); glPopMatrix()
    glPushMatrix(); glTranslatef(+fus_L*0.10, +fus_R*1.8, +fus_R*0.6); _draw_cylinder_x(eng_L*0.8, eng_R*0.8, rgb=pal['accent']); glPopMatrix()
    glPushMatrix(); glTranslatef(+fus_L*0.10, -fus_R*1.8, +fus_R*0.6); _draw_cylinder_x(eng_L*0.8, eng_R*0.8, rgb=pal['accent']); glPopMatrix()
    glPushMatrix(); glTranslatef(-fus_L*0.35, +fus_R*1.9, 0); _draw_box(tail_chord*0.5, 4, 6, rgb=pal['wing']); glPopMatrix()
    glPushMatrix(); glTranslatef(-fus_L*0.35, -fus_R*1.9, 0); _draw_box(tail_chord*0.5, 4, 6, rgb=pal['wing']); glPopMatrix()
    glPushMatrix(); glTranslatef(-fus_L*0.50, 0, 6); _draw_box(6, tail_span*0.55, 1.2, rgb=pal['wing']); glPopMatrix()

def build_enemy_MiG21(pal):
    fus_L, fus_R = 130, 10
    _draw_cylinder_x(fus_L, fus_R, rgb=pal['fus'])
    glPushMatrix(); glTranslatef(+fus_L*0.5,0,0); _draw_cone_x(36, fus_R*1.05, rgb=pal['accent']); glPopMatrix()
    span = 90
    tris = [((-10, -span*0.5, 0), (30, 0, 0), (-10,  span*0.5, 0)),
            ((-20, -span*0.3, 0), ( -5, 0, 0), (-20,  span*0.3, 0))]
    _draw_flat_tris(tris, rgb=pal['wing'])
    glPushMatrix(); glTranslatef(-40,0,0); _draw_box(10, 1.5, 10, rgb=pal['wing']); glPopMatrix()
    glPushMatrix(); glTranslatef(-35, +20, 0); _draw_box(8, 18, 1.0, rgb=pal['wing']); glPopMatrix()
    glPushMatrix(); glTranslatef(-35, -20, 0); _draw_box(8, 18, 1.0, rgb=pal['wing']); glPopMatrix()

def build_enemy_F16(pal):
    fus_L, fus_R = 140, 12
    _draw_cylinder_x(fus_L, fus_R, rgb=pal['fus'])
    glPushMatrix(); glTranslatef(+fus_L*0.5,0,0); _draw_cone_x(34, fus_R*1.0, rgb=pal['accent']); glPopMatrix()
    glPushMatrix(); glTranslatef(+10, 0, -fus_R*1.3); _draw_box(10, 12, 6, rgb=pal['accent'])
    glPopMatrix()
    glPushMatrix(); glTranslatef(-10,0,0); _draw_box(18, 85, 1.5, rgb=pal['wing']); glPopMatrix()
    glPushMatrix(); glTranslatef(-45,0,0); _draw_box(10, 2.0, 12, rgb=pal['wing']); glPopMatrix()
    glPushMatrix(); glTranslatef(-40, +22, 0); _draw_box(8, 20, 1.2, rgb=pal['wing']); glPopMatrix()
    glPushMatrix(); glTranslatef(-40, -22, 0); _draw_box(8, 20, 1.2, rgb=pal['wing']); glPopMatrix()

def build_enemy_Rafale(pal):
    fus_L, fus_R = 145, 12
    _draw_cylinder_x(fus_L, fus_R, rgb=pal['fus'])
    glPushMatrix(); glTranslatef(+fus_L*0.5,0,0); _draw_cone_x(32, fus_R*1.05, rgb=pal['accent']); glPopMatrix()
    glPushMatrix(); glTranslatef(+15, +28, 0); _draw_box(6, 20, 1.0, rgb=pal['wing']); glPopMatrix()
    glPushMatrix(); glTranslatef(+15, -28, 0); _draw_box(6, 20, 1.0, rgb=pal['wing']); glPopMatrix()
    glPushMatrix(); glTranslatef(-5, 0, 0); _draw_box(20, 90, 1.5, rgb=pal['wing']); glPopMatrix()
    glPushMatrix(); glTranslatef(-55,0,0); _draw_box(10, 2.0, 13, rgb=pal['wing']); glPopMatrix()

# Map type -> builder & color accents if needed later
ENEMY_BUILDERS = {
    'A10'    : build_enemy_A10,
    'MiG21'  : build_enemy_MiG21,
    'F16'    : build_enemy_F16,
    'Rafale' : build_enemy_Rafale,
}

# Active enemies
enemies = []

# Spawner params (distances widened for big world)
ENEMY_MAX_COUNT   = 10
ENEMY_SPAWN_RATE  = 0.60   # enemies per second (average)
ENEMY_MIN_ALT     = 200.0
ENEMY_MAX_ALT     = 3500.0
ENEMY_SPEEDS      = {'A10': 260.0, 'MiG21': 520.0, 'F16': 560.0, 'Rafale': 580.0}
ENEMY_PATTERNS    = ['straight','zigzag']

def _random_enemy_type():
    return random.choice(list(ENEMY_BUILDERS.keys()))

def _spawn_enemy_ahead():
    (fx,fy,fz), _, _ = rotation_matrix(yaw_deg, 0.0, 0.0)
    # Spawn just beyond visual range, inside radar
    dist_min = 1.2 * VISUAL_RANGE
    dist_max = 2.0 * VISUAL_RANGE
    dist_ahead = random.uniform(dist_min, dist_max)
    lateral    = random.uniform(-0.4 * dist_ahead, 0.4 * dist_ahead)

    rightx, righty = +fy, -fx
    spawn_p = [pos[0] + fx*dist_ahead + rightx*lateral,
               pos[1] + fy*dist_ahead + righty*lateral,
               clamp(pos[2] + random.uniform(-300.0, 800.0), ENEMY_MIN_ALT, ENEMY_MAX_ALT)]
    t = _random_enemy_type()
    spd = ENEMY_SPEEDS[t]
    pattern = random.choice(ENEMY_PATTERNS)
    to_player = (pos[0]-spawn_p[0], pos[1]-spawn_p[1])
    yaw = rad2deg(math.atan2(to_player[1], to_player[0]))
    scale = TYPE_META[t]['scale']
    hit_r = BASE_HIT_R[t] * scale
    return {
        'type': t, 'name': TYPE_META[t]['name'],
        'p': spawn_p[:], 'yaw': yaw, 'pitch': 0.0, 'roll': 0.0,
        'speed': spd, 'pattern': pattern,
        't0': time.time(), 'phase': random.random()*math.tau,
        'hit_r': hit_r, 'scale': scale,
    }

# Canonical unscaled hit radii (from original small models)
BASE_HIT_R = {'A10':70.0, 'MiG21':60.0, 'F16':65.0, 'Rafale':68.0}

# Enemy palettes and meta (scale vs F-117; display name; base colors)
TYPE_META = {
    'A10'    : {'name':'A-10 Warthog',    'scale':0.90, 'colors':{'fus':(0.55,0.60,0.62), 'wing':(0.62,0.66,0.68), 'accent':(0.30,0.35,0.38)}},
    'MiG21'  : {'name':'MiG-21',          'scale':0.80, 'colors':{'fus':(0.70,0.74,0.78), 'wing':(0.72,0.76,0.80), 'accent':(0.20,0.60,0.20)}},
    'F16'    : {'name':'F-16',            'scale':0.90, 'colors':{'fus':(0.64,0.68,0.72), 'wing':(0.66,0.70,0.74), 'accent':(0.85,0.10,0.10)}},
    'Rafale' : {'name':'Rafale',          'scale':0.95, 'colors':{'fus':(0.60,0.66,0.72), 'wing':(0.62,0.68,0.74), 'accent':(0.10,0.45,0.85)}},
}



_enemy_uid = 1
def _assign_enemy_id(e):
    global _enemy_uid
    e['id'] = _enemy_uid
    _enemy_uid += 1
    return e



def spawn_enemy():
    e = _assign_enemy_id(_spawn_enemy_ahead())
    enemies.append(e)


# For poisson-like spawn timing
_enemy_spawn_accum = 0.0
def _maybe_spawn(dt):
    global _enemy_spawn_accum
    if len(enemies) >= ENEMY_MAX_COUNT: return
    _enemy_spawn_accum += dt * ENEMY_SPAWN_RATE
    while _enemy_spawn_accum >= 1.0:
        spawn_enemy()
        _enemy_spawn_accum -= 1.0

def _dir_from_yaw(yaw):
    cy, sy = math.cos(deg2rad(yaw)), math.sin(deg2rad(yaw))
    return (cy, sy, 0.0)

def _bullet_hits_enemy(b, e):
    # Simple sphere bound (later: replace with AABB/OBB)
    dx = b['p'][0]-e['p'][0]; dy = b['p'][1]-e['p'][1]; dz = b['p'][2]-e['p'][2]
    return (dx*dx + dy*dy + dz*dz) <= (e['hit_r']*e['hit_r'])

def _bullet_hit_any_ground(b):
    px,py,pz = b['p']
    # tower body: cylinder test (2D)
    for i,t in enumerate(towers):
        dx = px - t['p'][0]; dy = py - t['p'][1]
        if (dx*dx+dy*dy) <= (t['r']+8.0)**2 and pz <= (t['h']+GROUND_PLANE_Z+30.0):
            mark_tower_hit(i, by_player=True); return True

    # tower AA / scattered AA / SAM / bunkers: small sphere / box-ish check
    def near2(p, u, z, r):
        return ( (p[0]-u['p'][0])**2 + (p[1]-u['p'][1])**2 + (z - z)**2 ) <= r*r
    for u in tower_aas:
        if ( (px-u['p'][0])**2 + (py-u['p'][1])**2 + (pz-u['p'][2])**2 ) <= (40.0**2):
            u['hp'] = u.get('hp',100) - BULLET_DAMAGE; return True
    for u in aa_units:
        if ( (px-u['p'][0])**2 + (py-u['p'][1])**2 + (pz-u['z'])**2 ) <= (38.0**2):
            u['hp'] = u.get('hp',100) - BULLET_DAMAGE; return True
    for u in sam_units:
        if ( (px-u['p'][0])**2 + (py-u['p'][1])**2 + (pz-u['z'])**2 ) <= (45.0**2):
            u['hp'] = u.get('hp',160) - BULLET_DAMAGE; return True
    for u in bunkers:
        if ( (px-u['p'][0])**2 + (py-u['p'][1])**2 + (pz-(u['z']+12.0))**2 ) <= (60.0**2):
            u['hp'] = u.get('hp',220) - BULLET_DAMAGE; return True
    return False





def update_enemies(dt):
    global score
    _maybe_spawn(dt)
    if not enemies: return
    keep = []
    for e in enemies:
        # ensure HP fields exist
        if 'hp' not in e:
            e['hp_max'] = 120
            e['hp']     = 120

        fx, fy, _ = _dir_from_yaw(e['yaw'])

        # movement
        e['p'][0] += fx * e['speed'] * dt
        e['p'][1] += fy * e['speed'] * dt

        # pattern
        t = time.time() - e['t0']
        if e['pattern'] == 'zigzag':
            amp = 220.0; freq = 0.5
            rx, ry = +fy, -fx
            e['p'][0] += rx * math.sin((t+e['phase'])*2.0*math.pi*freq) * dt * amp
            e['p'][1] += ry * math.sin((t+e['phase'])*2.0*math.pi*freq) * dt * amp

        # altitude wiggle & clamp
        e['p'][2] = clamp(e['p'][2] + math.sin((t+e['phase'])*0.7) * 12.0 * dt, ENEMY_MIN_ALT, ENEMY_MAX_ALT)
        e['p'][2] = clamp(e['p'][2], PLAYER_ALT_MIN + 5.0, ENEMY_MAX_ALT)


        # hard floor over actual terrain so enemies never dip into mountains
        terr = terrain_h(e['p'][0], e['p'][1])
        min_clear = 120.0
        if e['p'][2] < terr + min_clear:
            e['p'][2] = terr + min_clear

        # tower cylinder collision → treat as crash
        ti = _hit_tower_cylinder(e['p'])
        if ti >= 0:
            # explode and skip keeping this enemy
            spawn_explosion(e['p'], base_radius=100.0, ttl=0.8, kind='aircraft')
            e['hp'] = 0




        # Player ↔ enemy collision: per-second tick (not per-frame)
        if player_enemy_collision(e):
            dmg = RAM_DMG_RATE * dt
            e['hp'] = e.get('hp', 120) - dmg
            player_take_damage(dmg, cause="ram")
            # small spark while grinding
            spawn_explosion(e['p'], base_radius=40.0, ttl=0.25, kind='generic')





        # cull far beyond radar
        if math.hypot(e['p'][0] - pos[0], e['p'][1] - pos[1]) > RADAR_RANGE * 1.2:
            continue

        # keep within play area
        margin = GROUND_EXTENT * 0.98
        x, y = e['p'][0], e['p'][1]
        out = (abs(x) > margin) or (abs(y) > margin)
        if out:
            target_x = clamp(x, -GROUND_EXTENT*0.95, GROUND_EXTENT*0.95)
            target_y = clamp(y, -GROUND_EXTENT*0.95, GROUND_EXTENT*0.95)
            _steer_towards(e, (target_x, target_y), rate_deg_per_s=45.0, dt=dt)

        # cull out-of-bounds
        if abs(x) > GROUND_EXTENT*1.05 or abs(y) > GROUND_EXTENT*1.05:
            continue

        # bullet collisions -> apply damage (no insta-kill)
        if bullets:
            for b in bullets:
                if _bullet_hits_enemy(b, e):
                    e['hp'] -= BULLET_DAMAGE
                    score += 1                 # +1 per hit
                    b['t0'] = 0.0              # retire bullet
                    break                       # one bullet, one hit

        if e['hp'] > 0:
            keep.append(e)
        else:
            # enemy destroyed (no extra score now; we can add kill bonus later)
            spawn_explosion(e['p'], base_radius=100.0, ttl=0.8, kind='aircraft')

          

    enemies[:] = keep

def _push_at(p, yaw, pitch=0.0, roll=0.0):
    glPushMatrix()
    glTranslatef(p[0], p[1], p[2])
    glRotatef(yaw, 0,0,1); glRotatef(-pitch,0,1,0); glRotatef(roll,1,0,0)

def draw_enemy(e):
    """Render one enemy using its type-specific builder and color palette."""
    was_cull = glIsEnabled(GL_CULL_FACE)
    glDisable(GL_LIGHTING)
    if was_cull: glDisable(GL_CULL_FACE)

    # Position & orient in world (this pushes the matrix)
    _push_at(e['p'], e['yaw'], e.get('pitch', 0.0), e.get('roll', 0.0))

    # Scale + draw
    s   = e.get('scale', 1.0)
    glScalef(s, s, s)
    t   = e['type']
    pal = TYPE_META[t]['colors']
    ENEMY_BUILDERS[t](pal)

    # Pop the matrix pushed by _push_at
    glPopMatrix()
    if was_cull: glEnable(GL_CULL_FACE)




def draw_enemies():
    if not enemies: return
    was_cull = glIsEnabled(GL_CULL_FACE)
    glDisable(GL_LIGHTING)
    if was_cull: glDisable(GL_CULL_FACE)

    for e in enemies:
        draw_enemy(e)
        # 2D screen overlay: name + health bar
        scr = _project_to_screen(e['p'][0], e['p'][1], e['p'][2] + 20.0)
        if not scr: 
            continue
        sx, sy = scr

        # name
        draw_screen_text(sx - 20, sy + 14, e['name'], color=(0,0,0))

        # health bar under name (red fill on dark background)
        _hud_begin()
        w = 60.0; h = 6.0
        x0 = sx - w*0.5; y0 = sy + 2.0
        # background
        glColor3f(0.15, 0.15, 0.15)
        glBegin(GL_QUADS)
        glVertex2f(x0, y0); glVertex2f(x0+w, y0); glVertex2f(x0+w, y0+h); glVertex2f(x0, y0+h)
        glEnd()
        # fill
        pct = 1.0
        if 'hp' in e and 'hp_max' in e and e['hp_max'] > 0:
            pct = max(0.0, min(1.0, e['hp'] / float(e['hp_max'])))
        glColor3f(0.9, 0.1, 0.1)
        glBegin(GL_QUADS)
        glVertex2f(x0, y0); glVertex2f(x0 + w*pct, y0); glVertex2f(x0 + w*pct, y0+h); glVertex2f(x0, y0+h)
        glEnd()
        _hud_end()

    if was_cull: glEnable(GL_CULL_FACE)



# ---------------- Helpers ----------------

def _hp_and_label_for_tid(tid):
    """Return (hp, hp_max, label_str) for either AIR or ground tid."""
    if tid is None:
        return None, None, ""
    if isinstance(tid, int) or (isinstance(tid, tuple) and tid[0] == 'AIR'):
        eid = tid if isinstance(tid, int) else tid[1]
        e = _enemy_by_id(eid)
        if not e: return None, None, "AIR"
        return e.get('hp'), e.get('hp_max'), TYPE_META[e['type']]['name']
    kind, gid = tid
    u = _ground_by_id(gid)
    lbl = kind
    if not u: return None, None, lbl
    return u.get('hp'), u.get('hp_max'), lbl




def crosshair_hits_any_enemy():
    """Return True if the center ray (from nose, forward) intersects ANY enemy hit sphere.
       Ignores distance/range; only geometry matters."""
    if not enemies: 
        return False
    (fx,fy,fz), _, _ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)

    # start a bit ahead of the jet to avoid self-hit
    NOSE = 90.0
    sx = pos[0] + fx*NOSE
    sy = pos[1] + fy*NOSE
    sz = pos[2] + fz*NOSE

    for e in enemies:
        wx = e['p'][0] - sx; wy = e['p'][1] - sy; wz = e['p'][2] - sz
        t  = wx*fx + wy*fy + wz*fz          # projection onto the ray
        if t <= 0.0:                         # behind us
            continue
        px = sx + fx*t; py = sy + fy*t; pz = sz + fz*t
        dx = e['p'][0] - px; dy = e['p'][1] - py; dz = e['p'][2] - pz
        if (dx*dx + dy*dy + dz*dz) <= (e['hit_r'] * e.get('aim_slop', 1.0))**2:
            return True
    return False





def cycle_target(direction=+1):
    """Cycle targets within the current missile's class (A2A: AIR/TAA, A2S: ground only)."""
    global _target_id, _lock_timer, _lock_state
    m = MISSILES[MSL_SELECTED]
    allow = ['AIR', 'TAA'] if MSL_SELECTED in ('A2A_S', 'A2A_M') else ['TAA', 'AA', 'SAM', 'BUNKER']

    cands = _front_cone_candidates_any(cone_deg=m['lock_cone_deg'], max_range=None, allow=allow)
    if not cands:
        _target_id, _lock_timer, _lock_state = None, 0.0, 'NONE'
        return

    ids = [tid for (tid, _err) in cands]
    if _target_id in ids:
        i = ids.index(_target_id)
        _target_id = ids[(i + direction) % len(ids)]
    else:
        _target_id = ids[0]

    _lock_timer = 0.0
    # classify as OUT/ACQ immediately based on range
    tp = _resolve_target_pos(_target_id)
    if tp:
        d = math.sqrt((tp[0]-pos[0])**2 + (tp[1]-pos[1])**2 + (tp[2]-pos[2])**2)
        _lock_state = 'ACQ' if d <= m['lock_range'] else 'OUT'
    else:
        _lock_state = 'NONE'





def draw_weapon_status():
    if cam_mode != 'first': return
    _hud_begin()
    m = MISSILES[MSL_SELECTED]; ammo = MSL_AMMO[MSL_SELECTED]
    txt = f"{m['name']}   AMMO {ammo:02d}   LOCK: {_lock_state}"
    x = WIN_W*0.5 - 150; y = 36
    draw_screen_text(x, y, txt, color=(0.9, 0.95, 0.9))
    _hud_end()


def draw_player_health():
    _hud_begin()
    x, y = 18, 34
    w, h = 240.0, 12.0
    # bg
    glColor3f(0.12,0.12,0.12)
    glBegin(GL_QUADS)
    glVertex2f(x,y); glVertex2f(x+w,y); glVertex2f(x+w,y+h); glVertex2f(x,y+h)
    glEnd()
    # fill
    pct = max(0.0, min(1.0, player_hp / float(PLAYER_HP_MAX)))
    glColor3f(0.9,0.2,0.2)
    glBegin(GL_QUADS)
    glVertex2f(x,y); glVertex2f(x+w*pct,y); glVertex2f(x+w*pct,y+h); glVertex2f(x,y+h)
    glEnd()
    # text (+ invincible flag)
    txt = f"HP {int(player_hp)}/{PLAYER_HP_MAX}" + ("  [INV]" if PLAYER_INVINCIBLE else "")
    draw_screen_text(x + 6, y + h + 6, txt, color=(0.95,0.95,1.0))
    _hud_end()



def release_missile_trigger():
    """Fire on release: LOCK at release => homing; else straight."""
    globals()['msl_armed'] = False
    fire_missile()










def drop_flare():
    # Spawn a billboard behind the player along -forward
    (fx,fy,fz),_,_ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)
    back = [pos[0] - fx*70.0, pos[1] - fy*70.0, pos[2] - fz*30.0]
    flares.append({'p': back[:], 'dir': [fx,fy,fz], 't': 0.0, 'life': FLARE_LIFE})

def update_flares(dt):
    if not flares: return
    keep=[]
    for f in flares:
        f['t'] += dt
        if f['t'] < f['life']:
            # trail slightly with aircraft motion for feel (optional)
            keep.append(f)
    flares[:] = keep

def draw_flares():
    if not flares: return
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    for f in flares:
        # simple camera-facing quad
        cx, cy = WIN_W*0.5, WIN_H*0.5  # not used; draw in world-space
        # build right/up from current camera for billboard
        mv = glGetDoublev(GL_MODELVIEW_MATRIX)
        right = (mv[0][0], mv[1][0], mv[2][0])
        up    = (mv[0][1], mv[1][1], mv[2][1])
        w,h = FLARE_W, FLARE_H
        px,py,pz = f['p']
        vx = [px + right[0]*w*0.5, py + right[1]*w*0.5, pz + right[2]*w*0.5]
        vx2= [px - right[0]*w*0.5, py - right[1]*w*0.5, pz - right[2]*w*0.5]
        a  = [vx[0] + up[0]*h*0.5, vx[1] + up[1]*h*0.5, vx[2] + up[2]*h*0.5]
        b  = [vx2[0]+ up[0]*h*0.5, vx2[1]+ up[1]*h*0.5, vx2[2]+ up[2]*h*0.5]
        c  = [vx2[0]- up[0]*h*0.5, vx2[1]- up[1]*h*0.5, vx2[2]- up[2]*h*0.5]
        d  = [vx[0] - up[0]*h*0.5, vx[1] - up[1]*h*0.5, vx[2] - up[2]*h*0.5]
        # bright orange, fade with time
        alpha = max(0.0, 1.0 - (f['t']/f['life']))
        glColor4f(1.0, 0.55, 0.05, 0.6*alpha)
        glBegin(GL_QUADS)
        glVertex3f(*a); glVertex3f(*b); glVertex3f(*c); glVertex3f(*d)
        glEnd()
    glDisable(GL_BLEND)





def _nose_and_fwd():
    (fx,fy,fz),_,_ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)
    # spawn a bit ahead of the jet
    nose = [pos[0] + fx*90.0, pos[1] + fy*90.0, pos[2] + fz*90.0]
    fwd  = [fx, fy, fz]
    return nose, fwd

def _norm3(v):
    L = math.sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]) + 1e-9
    return [v[0]/L, v[1]/L, v[2]/L]

def _dot3(a,b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]

def _clamp(x, a, b): 
    return a if x < a else (b if x > b else x)








def fire_missile():
    """Fire currently selected missile. If locked, it homes; else it flies straight.
       After firing, retarget to the closest-in-cone-and-range candidate."""
    mkey = MSL_SELECTED
    if MSL_AMMO[mkey] <= 0:
        return  # no ammo
    spec = MISSILES[mkey]

    nose, fwd = _nose_and_fwd()
    vel = [fwd[0]*spec['speed'], fwd[1]*spec['speed'], fwd[2]*spec['speed']]
    tgt_id = _target_id if _lock_state == 'LOCK' else None




    missiles.append({
        'key': mkey, 'kind': spec['kind'], 'model': spec['model'],
        'pos': nose[:], 'vel': vel[:], 'speed': spec['speed'],
        'turn_dps': spec['turn_rate_dps'],
        'damage': spec['damage'], 'aoe': spec['aoe'], 'falloff': spec['falloff'],
        'hit_r': spec['hit_r'],
        'time': spec['time'], 'age': 0.0,
        'orig_target_id': _target_id if _lock_state == 'LOCK' else None,
        'target_id': _target_id if _lock_state == 'LOCK' else None,
        'target_flare': None,
        'trail': []
    })



    MSL_AMMO[mkey] -= 1

    # Reset to closest target in cone AND in-range after firing
    _retarget_after_fire()

def _retarget_after_fire():
    global _target_id, _lock_timer, _lock_state
    m = MISSILES[MSL_SELECTED]
    cands = _front_cone_candidates(cone_deg=m['lock_cone_deg'], max_range=m['lock_range'])
    if cands:
        _target_id = cands[0][0]['id']
        _lock_timer = 0.0
        _lock_state = 'ACQ'
    else:
        _target_id = None
        _lock_timer = 0.0
        _lock_state = 'NONE'





def _explode_missile(m):
    global score
    rad = max(0.0, m['aoe'])
    base = m['damage']
    fall = m.get('falloff','linear')

    # 1) Air enemies
    if enemies and rad > 0.0:
        for e in enemies:
            dx = e['p'][0]-m['pos'][0]; dy = e['p'][1]-m['pos'][1]; dz = e['p'][2]-m['pos'][2]
            d = math.sqrt(dx*dx+dy*dy+dz*dz)
            dmg = _aoe_damage_at(d, base, rad, fall)
            if dmg > 0.0:
                if 'hp' not in e: e['hp_max']=120; e['hp']=120
                e['hp'] -= dmg
                score += 1

    # 2) Player
    if not PLAYER_INVINCIBLE and rad > 0.0:
        dx = pos[0]-m['pos'][0]; dy = pos[1]-m['pos'][1]; dz = pos[2]-m['pos'][2]
        d = math.sqrt(dx*dx+dy*dy+dz*dz)
        dmg = _aoe_damage_at(d, base, rad, fall)
        if dmg > 0.0:
            player_take_damage(dmg, cause="missile")

    # 3) Ground objects (simple horizontal distance check)
    def _aoe_ground_list(lst, center, rad, base, fall, on_dead):
        keep=[]
        cx,cy,cz = center
        for u in lst:
            dx = u['p'][0]-cx; dy = u['p'][1]-cy
            d = math.hypot(dx,dy)
            dmg = _aoe_damage_at(d, base, rad, fall)
            if dmg > 0.0 and 'hp' in u:
                u['hp'] -= dmg
                global score
                score += 1
            if ('hp' in u and u['hp'] <= 0.0):
                on_dead(u)
            else:
                keep.append(u)
        return keep

    # towers: flip faction if body within AOE
    for i,t in enumerate(towers):
        dx = t['p'][0]-m['pos'][0]; dy = t['p'][1]-m['pos'][1]
        d  = math.hypot(dx,dy)
        if d <= (t['r'] + rad):
            mark_tower_hit(i, by_player=True)


    # AA on towers
    def _dead_taa(u): spawn_explosion([u['p'][0],u['p'][1],u['p'][2]], base_radius=90.0, ttl=0.6, kind='generic')
    tower_aas[:] = _aoe_ground_list(tower_aas, m['pos'], rad, base, fall, _dead_taa)

    # Scattered AA
    def _dead_aa(u): spawn_explosion([u['p'][0],u['p'][1],u['z']], base_radius=90.0, ttl=0.6, kind='generic')
    aa_units[:]   = _aoe_ground_list(aa_units,   m['pos'], rad, base, fall, _dead_aa)

    # SAM sites
    def _dead_sam(u): spawn_explosion([u['p'][0],u['p'][1],u['z']], base_radius=110.0, ttl=0.7, kind='generic')
    sam_units[:]  = _aoe_ground_list(sam_units,  m['pos'], rad, base, fall, _dead_sam)

    # Bunkers
    def _dead_b(u): spawn_explosion([u['p'][0],u['p'][1],u['z']+12.0], base_radius=130.0, ttl=0.8, kind='generic')
    bunkers[:]    = _aoe_ground_list(bunkers,    m['pos'], rad, base, fall, _dead_b)

    # FX
    ttl = 0.5 if m.get('model')=='arrow' else 0.7
    spawn_explosion(m['pos'], base_radius=min(140.0, rad*0.75), ttl=ttl, kind='missile')


def update_missiles(dt):
    if not missiles: return
    keep=[]
    for m in missiles:
        m['age'] += dt

        # --- guidance target selection (IR flare attraction) ---
        if m['kind'] == 'IR':
            # if already tracking a flare, keep it while alive; else search within seeker cone
            flr = None
            if m['target_flare'] is not None:
                for f in flares:
                    if id(f) == m['target_flare']:
                        flr = f; break
            if flr is None:
                # find a flare within IR seeker cone in front of missile direction
                if flares:
                    dcur = _norm3(m['vel'])
                    best=None; best_dp=0.0
                    for f in flares:
                        to = [f['p'][0]-m['pos'][0], f['p'][1]-m['pos'][1], f['p'][2]-m['pos'][2]]
                        to = _norm3(to)
                        dp = _dot3(dcur, to)
                        if dp >= math.cos(math.radians(IR_SEEKER_CONE_DEG)) and dp > best_dp:
                            best, best_dp = f, dp
                    if best is not None:
                        m['target_flare'] = id(best)
            else:
                # if flare expired, drop it and immediately re-pursue original plane (no cone check)
                pass




        # --- homing orientation ---
        desired_dir = None

        # player-targeting (SAM)
        if m.get('target_player'):
            desired_dir = _norm3([pos[0]-m['pos'][0], pos[1]-m['pos'][1], pos[2]-m['pos'][2]])


        # 1) if we have a flare target and it still exists -> pursue flare
        flr = None
        if m.get('target_flare') is not None:
            for f in flares:
                if id(f) == m['target_flare']:
                    flr = f; break
        if flr is not None:
            desired_dir = _norm3([flr['p'][0]-m['pos'][0], flr['p'][1]-m['pos'][1], flr['p'][2]-m['pos'][2]])
        else:
            # if flare lost and we had an original plane -> re-pursue it, no cone check
            if (m.get('target_flare') is not None) and (m.get('orig_target_id') is not None):
                m['target_id'] = m['orig_target_id']
                m['target_flare'] = None
            if m.get('target_id') is not None:
                tp = _resolve_target_pos(m['target_id'])
                if tp:
                    desired_dir = _norm3([tp[0]-m['pos'][0], tp[1]-m['pos'][1], tp[2]-m['pos'][2]])

        # 2) steer velocity toward desired_dir (if any)
        if desired_dir is not None:
            cur_dir = _norm3(m['vel'])
            cosang = _clamp(_dot3(cur_dir, desired_dir), -1.0, 1.0)
            ang = math.acos(cosang)
            max_turn = math.radians(m['turn_dps'] * dt)
            if ang > 1e-4:
                tfrac = 1.0 if ang <= max_turn else (max_turn/ang)
                new_dir = _norm3([cur_dir[0]*(1-tfrac)+desired_dir[0]*tfrac,
                                  cur_dir[1]*(1-tfrac)+desired_dir[1]*tfrac,
                                  cur_dir[2]*(1-tfrac)+desired_dir[2]*tfrac])
            else:
                new_dir = cur_dir
            m['vel'] = [new_dir[0]*m['speed'], new_dir[1]*m['speed'], new_dir[2]*m['speed']]

        # --- integrate ---
        m['pos'][0] += m['vel'][0]*dt
        m['pos'][1] += m['vel'][1]*dt
        m['pos'][2] += m['vel'][2]*dt

        # --- trail ---
        m['trail'].append(tuple(m['pos']))
        if len(m['trail']) > 8: m['trail'].pop(0)

        # --- body collision / proximity fuse vs enemies ---
        collided=False
        prox_hit=False
        if enemies:
            for e in enemies:
                dx = e['p'][0]-m['pos'][0]; dy = e['p'][1]-m['pos'][1]; dz = e['p'][2]-m['pos'][2]
                d2 = dx*dx+dy*dy+dz*dz
                # body collision
                if d2 <= (m['hit_r'] + 1.0)**2:
                    collided=True; break
                # proximity fuse
                fuse = max(4.0, 0.8*e['hit_r'])
                if d2 <= fuse*fuse:
                    prox_hit=True; break
        if collided or prox_hit:
            _explode_missile(m); continue
        
        
        # --- proximity to ground units (detonate near SAM/AA/BUNKER/TAA) ---
        if not collided and not prox_hit:
            fuse = 65.0  # reasonable small fuse sphere
            mp = m['pos']
            def near(lst, getz):
                for u in lst:
                    dx = u['p'][0]-mp[0]; dy=u['p'][1]-mp[1]; dz=getz(u)-mp[2]
                    if dx*dx+dy*dy+dz*dz <= fuse*fuse:
                        return True
                return False
            if (near(tower_aas, lambda u:u['p'][2]) or
                near(aa_units,  lambda u:u['z'])    or
                near(sam_units, lambda u:u['z'])    or
                near(bunkers,   lambda u:u['z']+12.0)):
                _explode_missile(m); 
                continue



        # --- IR collision with flare (explode on hit) ---
        if m['kind']=='IR' and flares:
            for f in flares:
                # approximate flare quad as a sphere with radius ~max(FLARE_W, FLARE_H)/2
                r = max(FLARE_W, FLARE_H)*0.5
                dx = f['p'][0]-m['pos'][0]; dy = f['p'][1]-m['pos'][1]; dz = f['p'][2]-m['pos'][2]
                if dx*dx+dy*dy+dz*dz <= (r + m['hit_r'])**2:
                    _explode_missile(m); 
                    # optional: remove the flare instantly on hit
                    try: flares.remove(f)
                    except: pass
                    collided=True
                    break
        if collided: 
            continue

        # --- ground collision (flat for now) ---
        # --- terrain/tower collision ---
        # collide with sculpted terrain
        if m['pos'][2] <= terrain_h(m['pos'][0], m['pos'][1]) + 1.0:
            _explode_missile(m); 
            continue

        # collide with tower cylinder (vertical) if within radius and height
        ti = _hit_tower_cylinder(m['pos'])
        if ti >= 0:
            _explode_missile(m)
            continue


        # --- fuel timeout ---
        if m['age'] >= m['time']:
            _explode_missile(m); continue

        keep.append(m)
    missiles[:] = keep






def draw_missiles():
    if not missiles: return
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE)

    def basis_from_dir(d):
        # build right/up roughly from world-up
        up_world = (0.0, 0.0, 1.0)
        right = _norm3([ up_world[1]*d[2]-up_world[2]*d[1],
                          up_world[2]*d[0]-up_world[0]*d[2],
                          up_world[0]*d[1]-up_world[1]*d[0] ])
        up = _norm3([ d[1]*right[2]-d[2]*right[1],
                      d[2]*right[0]-d[0]*right[2],
                      d[0]*right[1]-d[1]*right[0] ])
        return right, up

    for m in missiles:
        d = _norm3(m['vel'])
        right, up = basis_from_dir(d)
        p = m['pos']          # <-- define position for drawing
        r = right             # <-- alias to match the code that uses 'r'
        pulse = 1.0 + 0.35*math.sin(m['age']*12.0)


        # size per model (slightly bigger than before)
        L_tail = (20.0 if m['model']=='arrow' else 12.0) * pulse
        head_w = 4.0 if m['model']=='arrow' else 6.0
        head_h = 4.0 if m['model']=='arrow' else 6.0

        hx, hy, hz = m['pos']
        tx, ty, tz = hx - d[0]*L_tail, hy - d[1]*L_tail, hz - d[2]*L_tail

        # color per missile type (still friendly blue-ish but distinct)
        if m['key']=='A2A_S':  col = (0.35, 0.90, 1.00)   # bright cyan
        elif m['key']=='A2A_M':col = (0.20, 0.70, 1.00)   # deeper blue
        else:                   col = (0.50, 0.85, 1.00)   # pale blue (A2S)

        glColor3f(*col)

        if m.get('model') == 'arrow':
            # slim A2A arrow (triangle + tail)
            glColor3f(0.3, 0.9, 1.0) if not m.get('target_player') else glColor3f(1.0, 0.25, 0.25)
            s = 6.0
            glBegin(GL_TRIANGLES)
            glVertex3f(p[0] + d[0]*s*1.2, p[1] + d[1]*s*1.2, p[2] + d[2]*s*1.2)
            glVertex3f(p[0] - d[0]*s*0.6 - r[0]*s*0.5, p[1] - d[1]*s*0.6 - r[1]*s*0.5, p[2] - d[2]*s*0.6 - r[2]*s*0.5)
            glVertex3f(p[0] - d[0]*s*0.6 + r[0]*s*0.5, p[1] - d[1]*s*0.6 + r[1]*s*0.5, p[2] - d[2]*s*0.6 + r[2]*s*0.5)
            glEnd()
        elif m.get('model') == 'ammo':
            # fat A2S/SAM ammo (capsule-ish)
            glColor3f(0.85, 0.85, 0.95) if not m.get('target_player') else glColor3f(1.0, 0.35, 0.35)
            sL = 10.0  # length half
            sR = 4.0   # radius
            # body (quad strip along direction)
            glBegin(GL_QUADS)
            # side “ribs” using right/up vectors r,u (compute r,u from d as you do elsewhere)
            glVertex3f(p[0] - d[0]*sL - r[0]*sR, p[1] - d[1]*sL - r[1]*sR, p[2] - d[2]*sL - r[2]*sR)
            glVertex3f(p[0] + d[0]*sL - r[0]*sR, p[1] + d[1]*sL - r[1]*sR, p[2] + d[2]*sL - r[2]*sR)
            glVertex3f(p[0] + d[0]*sL + r[0]*sR, p[1] + d[1]*sL + r[1]*sR, p[2] + d[2]*sL + r[2]*sR)
            glVertex3f(p[0] - d[0]*sL + r[0]*sR, p[1] - d[1]*sL + r[1]*sR, p[2] - d[2]*sL + r[2]*sR)
            glEnd()
            # nose cap (triangle)
            glBegin(GL_TRIANGLES)
            glVertex3f(p[0] + d[0]*sL*1.4, p[1] + d[1]*sL*1.4, p[2] + d[2]*sL*1.4)
            glVertex3f(p[0] + r[0]*sR, p[1] + r[1]*sR, p[2] + r[2]*sR)
            glVertex3f(p[0] - r[0]*sR, p[1] - r[1]*sR, p[2] - r[2]*sR)
            glEnd()
        else:
            # fallback: small point
            glColor3f(0.8,0.8,0.9)
            glPointSize(3.0)
            glBegin(GL_POINTS); glVertex3f(p[0],p[1],p[2]); glEnd()


        # exhaust spark at tail
        glPointSize(4.0)
        glBegin(GL_POINTS); glVertex3f(tx,ty,tz); glEnd()

        # trail (fading)
        if m.get('trail') and len(m['trail']) >= 2:
            glBegin(GL_LINE_STRIP)
            for i,p in enumerate(m['trail']):
                a = (i+1)/float(len(m['trail'])+1)
                glColor4f(col[0], col[1], col[2], 0.20 + 0.55*a)
                glVertex3f(*p)
            glEnd()

    glDisable(GL_BLEND)









def _aoe_damage_at(dist, base, radius, falloff):
    if radius <= 1e-6: return 0.0
    t = max(0.0, 1.0 - dist/float(radius))
    if falloff == 'none':    return base if dist <= radius else 0.0
    if falloff == 'linear':  return base * t
    if falloff == 'shallow': return base * (t**0.5)
    return base * t








def spawn_explosion(pos, base_radius=80.0, ttl=0.7, kind='generic'):
    """Create a lowkey expanding ring + sparks explosion in world space."""
    explosions.append({'p': pos[:], 't': 0.0, 'ttl': ttl, 'r0': base_radius, 'kind': kind})

def update_explosions(dt):
    if not explosions: return
    keep=[]
    for ex in explosions:
        ex['t'] += dt
        if ex['t'] < ex['ttl']:
            keep.append(ex)
    explosions[:] = keep

def _billboard_axes():
    # camera right/up from current modelview
    mv = glGetDoublev(GL_MODELVIEW_MATRIX)
    right = (mv[0][0], mv[1][0], mv[2][0])
    up    = (mv[0][1], mv[1][1], mv[2][1])
    return right, up

def draw_explosions():
    if not explosions: return
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE)  # additive
    right, up = _billboard_axes()
    for ex in explosions:
        u = ex['t']/ex['ttl']        # 0..1
        r = ex['r0']*(0.6 + 0.9*u)   # grows over time
        # color per kind
        if ex['kind']=='aircraft':
            base = (1.0, 0.6, 0.1)
        elif ex['kind']=='missile':
            base = (0.9, 0.95, 1.0)
        else:
            base = (0.95, 0.8, 0.4)
        alpha = max(0.0, 1.0 - u) * 0.8

        px,py,pz = ex['p']
        # ring (line loop)
        seg = 32
        glColor4f(base[0], base[1], base[2], alpha*0.8)
        glBegin(GL_LINE_LOOP)
        for i in range(seg):
            th = 2.0*math.pi*i/seg
            vx = (right[0]*math.cos(th) + up[0]*math.sin(th))*r
            vy = (right[1]*math.cos(th) + up[1]*math.sin(th))*r
            vz = (right[2]*math.cos(th) + up[2]*math.sin(th))*r
            glVertex3f(px+vx, py+vy, pz+vz)
        glEnd()
        # soft core (billboard quad)
        w = r*0.8; h = r*0.8
        a = (px + right[0]*w*0.5 + up[0]*h*0.5,
             py + right[1]*w*0.5 + up[1]*h*0.5,
             pz + right[2]*w*0.5 + up[2]*h*0.5)
        b = (px - right[0]*w*0.5 + up[0]*h*0.5,
             py - right[1]*w*0.5 + up[1]*h*0.5,
             pz - right[2]*w*0.5 + up[2]*h*0.5)
        c = (px - right[0]*w*0.5 - up[0]*h*0.5,
             py - right[1]*w*0.5 - up[1]*h*0.5,
             pz - right[2]*w*0.5 - up[2]*h*0.5)
        d = (px + right[0]*w*0.5 - up[0]*h*0.5,
             py + right[1]*w*0.5 - up[1]*h*0.5,
             pz + right[2]*w*0.5 - up[2]*h*0.5)
        glColor4f(base[0], base[1], base[2], alpha*0.35)
        glBegin(GL_QUADS); glVertex3f(*a); glVertex3f(*b); glVertex3f(*c); glVertex3f(*d); glEnd()

        # few sparks
        glPointSize(3.0)
        glColor4f(base[0], base[1], base[2], alpha)
        glBegin(GL_POINTS)
        for i in range(6):
            th = (i*math.pi/3.0) + ex['t']*6.0
            glVertex3f(px + math.cos(th)*r*0.6, py + math.sin(th)*r*0.6, pz + (0.2-math.fabs(math.sin(th))*0.2)*r*0.2)
        glEnd()
    glDisable(GL_BLEND)




def _prune_dead_ground():
    def prune(lst, z_off=0.0):
        keep=[]
        for u in lst:
            if 'hp' in u and u['hp'] <= 0.0:
                px,py = u['p']; pz = (u['p'][2] if 'p' in u and len(u['p'])>2 else u.get('z',0.0)) + z_off
                spawn_explosion([px,py,pz], base_radius=100.0, ttl=0.6, kind='generic')
            else:
                keep.append(u)
        return keep
    tower_aas[:] = prune(tower_aas, 0.0)
    aa_units[:]  = prune(aa_units, 0.0)
    sam_units[:] = prune(sam_units, 0.0)
    bunkers[:]   = prune(bunkers, 12.0)






def _axes_from_ypr(yaw, pitch, roll):
    # rotation_matrix is already in your code; it returns (fwd), (right), (up)
    fwd, right, up = rotation_matrix(yaw, pitch, roll)
    return fwd, right, up

def _add3(a,b):  return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def _mul3s(v,s): return (v[0]*s, v[1]*s, v[2]*s)

def _point_local_to_world(origin, fwd, right, up, p_local):
    # p_local = (fx, ry, uz) in aircraft local axes
    return (
        origin[0] + fwd[0]*p_local[0] + right[0]*p_local[1] + up[0]*p_local[2],
        origin[1] + fwd[1]*p_local[0] + right[1]*p_local[1] + up[1]*p_local[2],
        origin[2] + fwd[2]*p_local[0] + right[2]*p_local[1] + up[2]*p_local[2],
    )

def _draw_obb(center_world, half, fwd, right, up, color=(0.1,1.0,0.1)):
    # build 8 corners from half-extents along local axes
    hx, hy, hz = half
    corners_local = [
        (+hx,+hy,+hz), (+hx,-hy,+hz), (-hx,-hy,+hz), (-hx,+hy,+hz),  # top ring
        (+hx,+hy,-hz), (+hx,-hy,-hz), (-hx,-hy,-hz), (-hx,+hy,-hz),  # bottom ring
    ]
    corners = [ _point_local_to_world(center_world, fwd, right, up, c) for c in corners_local ]
    glDisable(GL_LIGHTING)
    glColor3f(*color); glLineWidth(1.5)
    # draw 12 edges
    idx = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    glBegin(GL_LINES)
    for a,b in idx:
        glVertex3f(*corners[a]); glVertex3f(*corners[b])
    glEnd()

def _draw_wire_sphere(center, r, color=(1.0,0.4,0.2)):
    # simple 3 great-circles for enemy hit spheres
    glDisable(GL_LIGHTING)
    glColor3f(*color); seg = 32
    cx,cy,cz = center
    # XY plane
    glBegin(GL_LINE_LOOP)
    for i in range(seg):
        th = 2.0*math.pi*i/seg
        glVertex3f(cx + r*math.cos(th), cy + r*math.sin(th), cz)
    glEnd()
    # XZ plane
    glBegin(GL_LINE_LOOP)
    for i in range(seg):
        th = 2.0*math.pi*i/seg
        glVertex3f(cx + r*math.cos(th), cy, cz + r*math.sin(th))
    glEnd()
    # YZ plane
    glBegin(GL_LINE_LOOP)
    for i in range(seg):
        th = 2.0*math.pi*i/seg
        glVertex3f(cx, cy + r*math.cos(th), cz + r*math.sin(th))
    glEnd()












def draw_player_hitboxes():
    # oriented boxes for body + wings
    fwd, right, up = _axes_from_ypr(yaw_deg, pitch_deg, roll_deg)

    # Body OBB
    body_center = _point_local_to_world(pos, fwd, right, up, F117_BODY_OFFS)
    _draw_obb(body_center, F117_BODY_HALF, fwd, right, up, color=(0.1,1.0,0.1))

    # Wing slab OBB
    wing_center = _point_local_to_world(pos, fwd, right, up, F117_WING_OFFS)
    _draw_obb(wing_center, F117_WING_HALF, fwd, right, up, color=(0.2,0.9,1.0))









def draw_dev_hitboxes():
    if not SHOW_HITBOXES: 
        return
    # Player
    draw_player_hitboxes()

    # Enemies (use their existing spherical hit_r)
    if enemies:
        for e in enemies:
            _draw_wire_sphere(tuple(e['p']), e.get('hit_r', 60.0), color=(1.0,0.35,0.35))

    # Missiles (use their body radius)
    if missiles:
        for m in missiles:
            r = m.get('hit_r', 8.0)
            _draw_wire_sphere(tuple(m['pos']), r, color=(0.35,0.85,1.0))

    # Ground targets: will draw here later (SAM/AA/bunkers/towers)
    # e.g., iterate ground_units and draw _draw_obb / _draw_wire_sphere as appropriate



def _obb_sphere_intersect(center_world, half, fwd,right,up, sphere_c, sphere_r):
    # transform sphere center into local box coords
    vx = sphere_c[0]-center_world[0]; vy = sphere_c[1]-center_world[1]; vz = sphere_c[2]-center_world[2]
    lx = vx*fwd[0] + vy*fwd[1] + vz*fwd[2]
    ly = vx*right[0]+ vy*right[1]+ vz*right[2]
    lz = vx*up[0]   + vy*up[1]   + vz*up[2]
    # closest point on the box
    hx,hy,hz = half
    cx = clamp(lx, -hx, hx)
    cy = clamp(ly, -hy, hy)
    cz = clamp(lz, -hz, hz)
    dx = lx-cx; dy = ly-cy; dz = lz-cz
    return (dx*dx + dy*dy + dz*dz) <= (sphere_r*sphere_r)

def player_enemy_collision(e):
    """Return True if enemy sphere hits player body or wing OBB."""
    fwd,right,up = _axes_from_ypr(yaw_deg, pitch_deg, roll_deg)
    # body
    body_c = _point_local_to_world(pos, fwd,right,up, F117_BODY_OFFS)
    if _obb_sphere_intersect(body_c, F117_BODY_HALF, fwd,right,up, e['p'], e.get('hit_r',60.0)):
        return True
    # wing slab
    wing_c = _point_local_to_world(pos, fwd,right,up, F117_WING_OFFS)
    if _obb_sphere_intersect(wing_c, F117_WING_HALF, fwd,right,up, e['p'], e.get('hit_r',60.0)):
        return True
    return False







def reset_player():
    global player_hp, yaw_deg, pitch_deg, roll_deg
    # simple respawn: center high and restore hp
    pos[0], pos[1], pos[2] = 0.0, 0.0, 250.0
    yaw_deg = 0.0; pitch_deg = 0.0; roll_deg = 0.0
    player_hp = PLAYER_HP_MAX
    spawn_explosion([pos[0],pos[1],pos[2]], base_radius=120.0, ttl=0.7, kind='aircraft')




def resolve_player_collisions(dt):
    """Clamp player to terrain and towers.
       • Terrain impact => instant death (respawn)
       • Tower cylinder impact => 30 damage and gentle push-out
    """
    # Terrain height (robust vs any flat plane baseline)
    gz = max(terrain_h(pos[0], pos[1]), GROUND_PLANE_Z)
    if pos[2] <= gz + 2.0:
        if PLAYER_INVINCIBLE:
            pos[2] = gz + 2.0
        else:
            player_take_damage(9999, cause="terrain")  # triggers respawn
            pos[2] = gz + 2.0
        return

    # Towers: vertical cylinder at base z0 up to z0+h
    # (If your build has no towers yet, this loop is harmless.)
    for t in globals().get('towers', []):
        base = t.get('z0', GROUND_PLANE_Z)
        top  = base + t.get('h', 0.0)
        if not (base - 5.0 <= pos[2] <= top + 5.0):
            continue
        dx = pos[0] - t['p'][0]; dy = pos[1] - t['p'][1]
        r  = math.hypot(dx, dy); min_r = t.get('r', 0.0) + 8.0
        if r < min_r:
            # push outward so we don't stick
            if r < 1.0: r = 1.0
            k = min_r / r
            pos[0] = t['p'][0] + dx * k
            pos[1] = t['p'][1] + dy * k
            if not PLAYER_INVINCIBLE:
                player_take_damage(30, cause="tower")
            return







def player_take_damage(amount, cause=""):
    global player_hp
    if PLAYER_INVINCIBLE: 
        return
    player_hp -= float(amount)
    if player_hp <= 0.0:
        # boom + respawn
        spawn_explosion([pos[0],pos[1],pos[2]], base_radius=140.0, ttl=0.8, kind='aircraft')
        reset_player()










# --------- Terrain height (simple, cheap) ---------
def terrain_h(x, y):
    # base ridges (cheap trig noise)
    s = 0.0013
    ridges = (math.sin(x*s)*math.cos(y*s)*0.65 +
              math.cos(x*s*0.6)*math.sin(y*s*0.6)*0.45 +
              math.sin(x*s*1.7 + 1.3)*math.sin(y*s*1.9 - 0.8)*0.25)
    h0 = ridges * TERRAIN_MAX_H * TERRAIN_MOUNTAIN_GAIN

    # one smooth valley corridor near spawn
    vx, vy = math.cos(VALLEY_SEED_TH), math.sin(VALLEY_SEED_TH)     # along-valley unit
    nx, ny = -vy, vx                                                # perpendicular unit
    dx, dy = (x - VALLEY_CENTER[0]), (y - VALLEY_CENTER[1])
    t  = dx*vx + dy*vy   # signed distance along the valley
    d  = dx*nx + dy*ny   # signed distance across the valley
    w_ax = math.exp(-(t*t) / (2.0*(VALLEY_LEN*0.9)**2))            # axial window
    trench = -VALLEY_DEPTH * math.exp(-(d*d) / (2.0*(VALLEY_WIDTH**2))) * w_ax

    h = h0 + trench
    return max(GROUND_PLANE_Z, h*0.6 + GROUND_PLANE_Z)




def terrain_slope_deg(x, y, eps=3.0):
    h = terrain_h
    hx = (h(x+eps,y) - h(x-eps,y)) / (2.0*eps)
    hy = (h(x,y+eps) - h(x,y-eps)) / (2.0*eps)
    return math.degrees(math.atan(math.hypot(hx, hy)))





# ---- Simple terrain line-of-sight (LOS) check ----
def has_line_of_sight(a, b, clearance=25.0, step_xy=600.0):
    """
    Return True if straight line a->b stays above terrain everywhere (with a small clearance).
    a,b: [x,y,z] world points. step_xy≈ground tile size for sampling density.
    """
    ax, ay, az = a[0], a[1], a[2]
    bx, by, bz = b[0], b[1], b[2]
    dx, dy = (bx - ax), (by - ay)
    dist_xy = math.hypot(dx, dy)
    if dist_xy < 1e-3:
        return True
    samples = max(1, int(dist_xy / max(200.0, step_xy*0.8)))
    for i in range(1, samples):
        t = i / float(samples)
        x = ax + dx*t
        y = ay + dy*t
        z = az + (bz - az)*t
        if terrain_h(x, y) + clearance >= z:
            return False
    return True

















def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v
def deg2rad(a): return a * math.pi / 180.0
def rad2deg(a): return a * 180.0 / math.pi

def rotation_matrix(yaw, pitch, roll):
    cy, sy = math.cos(deg2rad(yaw)),   math.sin(deg2rad(yaw))
    cp, sp = math.cos(deg2rad(pitch)), math.sin(deg2rad(pitch))
    cr, sr = math.cos(deg2rad(roll)),  math.sin(deg2rad(roll))
    fx = cy*cp; fy = sy*cp; fz = sp
    rx = cy*sp*sr - sy*cr; ry = sy*sp*sr + cy*cr; rz = -cp*sr
    ux = -cy*sp*cr - sy*sr; uy = -sy*sp*cr + cy*sr; uz = cp*cr
    return (fx, fy, fz), (rx, ry, rz), (ux, uy, uz)

def yaw_rate_for_speed():
    t = (speed - SPEED_MIN) / max(1e-6, (SPEED_MAX - SPEED_MIN))
    t = clamp(t, 0.0, 1.0) ** 0.4
    return YAW_RATE_MIN + (YAW_RATE_MAX - YAW_RATE_MIN) * t

# Geometry helpers
def v_add(a,b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def v_sub(a,b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def v_mul(a,s): return (a[0]*s, a[1]*s, a[2]*s)
def v_len(a): return math.sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2])
def v_norm(a):
    L = v_len(a)+1e-12
    return (a[0]/L, a[1]/L, a[2]/L)
def v_lerp(a,b,t): return (a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]), a[2]+t*(b[2]-a[2]))
def v_cross(a,b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def v_dot(a,b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]


def tri_normal(a,b,c):
    """Return unit face normal for triangle (a,b,c)."""
    ux,uy,uz = (b[0]-a[0], b[1]-a[1], b[2]-a[2])
    vx,vy,vz = (c[0]-a[0], c[1]-a[1], c[2]-a[2])
    nx = uy*vz - uz*vy
    ny = uz*vx - ux*vz
    nz = ux*vy - uy*vx
    L = math.sqrt(nx*nx + ny*ny + nz*nz) + 1e-12
    return (nx/L, ny/L, nz/L)

def offset_point_along_normal(p, n, eps):
    return (p[0] + n[0]*eps, p[1] + n[1]*eps, p[2] + n[2]*eps)
def rotate_around_axis(p, a0, a1, deg):
    """Rotate point p around axis line passing through a0->a1 by 'deg'."""
    ang = deg2rad(deg)
    k = v_norm(v_sub(a1, a0))
    # Translate to origin
    x = v_sub(p, a0)
    # Rodrigues' rotation
    cosA = math.cos(ang); sinA = math.sin(ang)
    x_rot = (
        x[0]*cosA + (k[1]*x[2]-k[2]*x[1])*sinA + k[0]*v_dot(k,x)*(1-cosA),
        x[1]*cosA + (k[2]*x[0]-k[0]*x[2])*sinA + k[1]*v_dot(k,x)*(1-cosA),
        x[2]*cosA + (k[0]*x[1]-k[1]*x[0])*sinA + k[2]*v_dot(k,x)*(1-cosA),
    )
    return v_add(a0, x_rot)





def _enemy_by_id(eid):
    for e in enemies:
        if e.get('id') == eid:
            return e
    return None

def _resolve_target_pos(tid):
    """tid can be int (legacy air), or ('AIR'|'TAA'|'AA'|'SAM'|'BUNKER', gid). Returns [x,y,z] or None."""
    if tid is None: return None
    if isinstance(tid, int):
        e = _enemy_by_id(tid);  return e['p'][:] if e else None
    kind, gid = tid
    if kind == 'AIR':
        e = _enemy_by_id(gid);  return e['p'][:] if e else None
    u = _ground_by_id(gid)
    if not u: return None
    if kind == 'TAA':   return [u['p'][0], u['p'][1], u['p'][2]]
    if kind == 'AA':    return [u['p'][0], u['p'][1], u['z']]
    if kind == 'SAM':   return [u['p'][0], u['p'][1], u['z']]
    if kind == 'BUNKER':return [u['p'][0], u['p'][1], u['z']+12.0]
    return None

def _resolve_target_label(tid):
    if tid is None: return ""
    if isinstance(tid, int): return "AIR"
    return tid[0]


def _front_cone_candidates(cone_deg, max_range=None):
    """Return [(e, screen_err)] inside forward cone, sorted center-first, optionally within range, LOS-gated."""
    (fx,fy,fz), _, _ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)
    dot_min = math.cos(math.radians(cone_deg))
    cx, cy = WIN_W*0.5, WIN_H*0.5
    cands = []
    eye = [pos[0], pos[1], pos[2]]
    for e in enemies:
        vx = e['p'][0] - pos[0]; vy = e['p'][1] - pos[1]; vz = e['p'][2] - pos[2]
        L  = math.sqrt(vx*vx + vy*vy + vz*vz) + 1e-9
        if max_range and L > max_range:
            continue
        dp = (fx*vx + fy*vy + fz*vz) / L
        if dp < dot_min:
            continue
        # NEW: terrain LOS gate
        if not has_line_of_sight(eye, e['p'], clearance=30.0):
            continue
        scr = _project_to_screen(e['p'][0], e['p'][1], e['p'][2])
        if not scr:
            continue
        sx, sy = scr
        err = (sx - cx)*(sx - cx) + (sy - cy)*(sy - cy)
        cands.append((e, err))
    cands.sort(key=lambda t: t[1])
    return cands



def _front_cone_candidates_any(cone_deg, max_range, allow):
    (fx,fy,fz), _, _ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)
    dot_min = math.cos(math.radians(cone_deg))
    cx, cy = WIN_W*0.5, WIN_H*0.5
    cands = []
    eye = [pos[0], pos[1], pos[2]]

    def _try(world_p, tid):
        vx = world_p[0]-pos[0]; vy = world_p[1]-pos[1]; vz = world_p[2]-pos[2]
        L  = math.sqrt(vx*vx+vy*vy+vz*vz) + 1e-9
        if max_range and L > max_range: return
        dp = (fx*vx + fy*vy + fz*vz) / L
        if dp < dot_min: return
        # NEW: terrain LOS gate
        if not has_line_of_sight(eye, world_p, clearance=30.0):
            return
        scr = _project_to_screen(world_p[0], world_p[1], world_p[2])
        if not scr: return
        sx,sy = scr
        err = (sx-cx)*(sx-cx)+(sy-cy)*(sy-cy)
        cands.append((tid, err))

    if 'AIR' in allow:
        for e in enemies: _try(e['p'], ('AIR', e['id']))
    if 'TAA' in allow:
        for u in tower_aas: _try([u['p'][0],u['p'][1],u['p'][2]], ('TAA', u['id']))
    if 'AA' in allow:
        for u in aa_units: _try([u['p'][0],u['p'][1],u['z']], ('AA', u['id']))
    if 'SAM' in allow:
        for u in sam_units: _try([u['p'][0],u['p'][1],u['z']], ('SAM', u['id']))
    if 'BUNKER' in allow:
        for u in bunkers: _try([u['p'][0],u['p'][1],u['z']+12.0], ('BUNKER', u['id']))

    cands.sort(key=lambda t:t[1])
    return cands









# ---------------- Ground (streamed tiles) ----------------
def draw_ground(center_x, center_y):
    glDisable(GL_LIGHTING)
    step = GROUND_STEP
    half = GROUND_EXTENT
    # compute player's current tile indices
    cx = int(math.floor(center_x / step))
    cy = int(math.floor(center_y / step))
    
    R0 = GROUND_PATCH_RADIUS_STEPS
    R  = min(R0, 12 + int(abs(pos[2]) / 2500.0))  # small patch low, grows with altitude, capped by R0

    # draw a patch around the player (non-planar tiles)
    for i in range(cx - R, cx + R + 1):
        x0 = i * step
        if x0 < -half or x0 > half: continue
        for j in range(cy - R, cy + R + 1):
            y0 = j * step
            if y0 < -half or y0 > half: continue
            x1 = x0 + step; y1 = y0 + step

            # heights at 4 corners
            z00 = terrain_h(x0, y0)
            z10 = terrain_h(x1, y0)
            z11 = terrain_h(x1, y1)
            z01 = terrain_h(x0, y1)

            # checker tint
            if ((i + j) & 1):
                glColor3f(0.82, 0.82, 0.82)
            else:
                glColor3f(0.74, 0.74, 0.74)

            # two triangles for a non-planar quad
            glBegin(GL_TRIANGLES)
            glVertex3f(x0, y0, z00); glVertex3f(x1, y0, z10); glVertex3f(x1, y1, z11)
            glVertex3f(x0, y0, z00); glVertex3f(x1, y1, z11); glVertex3f(x0, y1, z01)
            glEnd()







# --------- Procedural world placement ---------
def _rand_xy(radius=PLAY_EXTENT*0.8):
    a = random.random()*math.tau
    r = (random.random()**0.5) * radius
    return math.cos(a)*r, math.sin(a)*r



def _rand_xy_on_slope(min_deg, max_deg, radius, tries=80):
    for _ in range(tries):
        x,y = _rand_xy(radius)
        s = terrain_slope_deg(x,y)
        if min_deg <= s <= max_deg:
            return x,y
    return _rand_xy(radius)

def _nudge_near_on_slope(cx,cy,rad,min_deg,max_deg,tries=60):
    for _ in range(tries):
        th = random.random()*math.tau
        r  = (random.random()**0.5) * rad
        x  = cx + math.cos(th)*r
        y  = cy + math.sin(th)*r
        s  = terrain_slope_deg(x,y)
        if min_deg <= s <= max_deg:
            return x,y
    return cx,cy




def _hit_tower_cylinder(p):
    # collide with tower body? -> instant death unless invincible
    for i,t in enumerate(towers):
        x,y,z = p
        tx,ty = t['p']
        d2 = (x-tx)**2 + (y-ty)**2
        base = t.get('z0', GROUND_PLANE_Z)
        if d2 <= (t['r']+12.0)**2 and z <= base + t['h']:
            return i
        
    return -1

def update_world(dt):
    global PLAYER_HP
    # Player vs terrain/tower
    if not PLAYER_INVINCIBLE:
        # ground/terrain instant death
        if pos[2] <= terrain_h(pos[0], pos[1]) + 3.0:
            PLAYER_HP = 0
        # tower cylinder
        ti = _hit_tower_cylinder(pos)
        if ti >= 0:
            PLAYER_HP = 0

    # Loiter: flip tower to friend after 20s within 5km with no hits
    for t in towers:
        dist = math.hypot(pos[0]-t['p'][0], pos[1]-t['p'][1])
        if dist <= 5_000.0:
            t['loiter_t'] += dt
            if t['faction']==FACTION_FOE and t['loiter_t'] >= 20.0 and (time.time()-t['last_hit']>20.0):
                t['faction'] = FACTION_FRIEND
        else:
            t['loiter_t'] = max(0.0, t['loiter_t'] - dt*0.5)  # decay

def mark_tower_hit(tower_idx, by_player=True):
    """Register a hit on a tower. Player shots outside no-fire bubble do not flip."""
    t = towers[tower_idx]
    if by_player:
        dist = math.hypot(pos[0]-t['p'][0], pos[1]-t['p'][1])
        if dist > TOWER_NOFIRE_R:
            return  # safe poke: no faction change beyond 5km
    # inside bubble (or non-player hit) => hostile
    t['faction'] = FACTION_FOE
    t['last_hit'] = time.time()
    t['loiter_t'] = 0.0







def draw_world():
    glDisable(GL_LIGHTING)
    # Farther cull for tall towers; tighter for other ground objects
    OBJ_DRAW_DIST   = RADAR_RANGE * 1.5              # AA/SAM/Bunkers
    TOWER_DRAW_DIST = max(RADAR_RANGE * 4.0, 90000.0)  # Towers visible from far away
    OBJ_DRAW_DIST2   = OBJ_DRAW_DIST * OBJ_DRAW_DIST
    TOWER_DRAW_DIST2 = TOWER_DRAW_DIST * TOWER_DRAW_DIST



    # towers
    for i,t in enumerate(towers):
        x,y = t['p']; r=t['r']; h=t['h']

        dx = x - pos[0]; dy = y - pos[1]
        if (dx*dx + dy*dy) > TOWER_DRAW_DIST2: continue
        
            

        # column
        glColor3f(0.55,0.55,0.62) if t['faction']==FACTION_FRIEND else glColor3f(0.62,0.45,0.45)
        col = (0.55,0.55,0.62) if t['faction']==FACTION_FRIEND else (0.62,0.45,0.45)
        glPushMatrix(); glTranslatef(x, y, t.get('z0', GROUND_PLANE_Z))

        _draw_cylinder_z(h, r, slices=16, rgb=col)
        glPopMatrix()

    # AA pods on towers
    for a in tower_aas:
        x,y,z = a['p']; tw = towers[a['tower_idx']]
        glColor3f(0.1,0.1,1.0) if tw['faction']==FACTION_FRIEND else glColor3f(0.8,0.2,0.2)
        glPushMatrix(); glTranslatef(x,y,z); glutSolidCube(35.0); glPopMatrix()

    # scattered AA / SAM
    for u in aa_units:
        x,y = u['p']; z = u['z']
        glPushMatrix(); glTranslatef(x, y, z)
        # flat square pad (red enemy AA)
        s = 14.0
        glColor3f(1.0, 0.25, 0.25)
        glBegin(GL_QUADS)
        glVertex3f(-s, -s, 0.0); glVertex3f( s, -s, 0.0)
        glVertex3f( s,  s, 0.0); glVertex3f(-s,  s, 0.0)
        glEnd()
        # tiny upright “turret” nub
        glBegin(GL_QUADS)
        glVertex3f(-4, -4, 0.0); glVertex3f( 4, -4, 0.0)
        glVertex3f( 4,  4, 0.0); glVertex3f(-4,  4, 0.0)
        glEnd()
        glPopMatrix()


        dx = x - pos[0]; dy = y - pos[1]
        if (dx*dx + dy*dy) > OBJ_DRAW_DIST2: continue
        


        glColor3f(0.2,0.2,0.2); glPushMatrix(); glTranslatef(x,y,z); glutSolidTeapot(25.0); glPopMatrix()






    for u in sam_units:
        x,y = u['p']; z = u['z']

        dx = x - pos[0]; dy = y - pos[1]
        if (dx*dx + dy*dy) > OBJ_DRAW_DIST2: continue
        

        
        glPushMatrix(); glTranslatef(x,y,z)
        # color by state: loaded+aiming = bright, aiming+reloading = dim purple, idle = gray
        if u.get('aiming', False):
            glColor3f(0.95, 0.20, 0.20) if u.get('loaded', True) else glColor3f(0.40, 0.15, 0.60)
        else:
            glColor3f(0.25, 0.25, 0.28)
        glutSolidCone(30.0, 80.0, 8, 1)
        # show an aim ray when aiming
        if u.get('aiming', False):
            to = _norm3([pos[0]-x, pos[1]-y, pos[2]-z])
            glColor3f(0.9, 0.5, 1.0)
            glBegin(GL_LINES)
            glVertex3f(0,0,40)
            glVertex3f(to[0]*80.0, to[1]*80.0, 40 + to[2]*80.0)
            glEnd()
        glPopMatrix()






    # bunkers (trapezoid box)
    for b in bunkers:
        x,y = b['p']; z=b['z']

        dx = x - pos[0]; dy = y - pos[1]
        if (dx*dx + dy*dy) > OBJ_DRAW_DIST2: continue
        


        glPushMatrix(); glTranslatef(x,y,z+12.0); glScalef(120.0,90.0,60.0)
        glColor3f(0.25,0.25,0.25); glutSolidCube(1.0)
        glPopMatrix()






def world_init():
    random.seed(TERRAIN_SEED)

    # clear all world lists
    towers.clear(); tower_aas.clear()
    aa_units.clear(); sam_units.clear(); bunkers.clear()

    # --- Towers of God (vertical, base sits on local terrain) ---
    for _ in range(TOWER_COUNT):
        x, y = _rand_xy(PLACEMENT_RADIUS)
        z0   = terrain_h(x, y)
        towers.append({
            'p': [x, y],
            'z0': z0,                 # base height at terrain
            'r': TOWER_R,
            'h': TOWER_H,
            'faction': FACTION_FOE if random.random() < 0.5 else FACTION_FRIEND,
            'last_hit': -9999.0,
            'loiter_t': 0.0
        })
        # sprinkle 2–6 AA pods along the shaft, within sensible altitude
        n_pods = random.randint(2, 6)
        for _pod in range(n_pods):
            th = random.random() * math.tau
            z  = z0 + random.uniform(500.0, 6000.0)  # pod altitude above base
            tower_aas.append({
                'id': _new_gid(), 'class': 'TAA',
                'p': [x + TOWER_R * math.cos(th), y + TOWER_R * math.sin(th), z],
                'tower_idx': len(towers) - 1,
                'hp': 100, 'hp_max': 100,
                'cool': 0.0
            })

    # --- Scattered AA (half on valley/mountain walls, half anywhere) ---
    for i in range(AA_SCATTER):
        if i % 2 == 0:
            # “on the walls”: moderate slopes
            ax, ay = _rand_xy_on_slope(12.0, 35.0, PLACEMENT_RADIUS)
        else:
            # anywhere near spawn
            ax, ay = _rand_xy(PLACEMENT_RADIUS)
        aa_units.append({
            'id': _new_gid(), 'class': 'AA',
            'p': [ax, ay],
            'z': terrain_h(ax, ay),
            'hp': 100, 'hp_max': 100,
            'cool': 0.0
        })

    # --- Scattered SAM (prefer flats/benches and keep them far apart) ---
    spread = PLACEMENT_RADIUS
    taken  = []
    for _ in range(SAM_SCATTER):
        for _try in range(40):
            sx, sy = _rand_xy_on_slope(0.0, 10.0, spread)  # flat-ish
            # keep SAM sites well-separated
            if all((sx - tx) * (sx - tx) + (sy - ty) * (sy - ty) > (25_000.0 ** 2) for tx, ty in taken):
                taken.append((sx, sy))
                sam_units.append({
                    'id': _new_gid(), 'class': 'SAM',
                    'p': [sx, sy],
                    'z': terrain_h(sx, sy),
                    'hp': 160, 'hp_max': 160,
                    'cool': 0.0,
                    'loaded': True,
                    'aiming': False
                })
                break

    # --- One guarded bunker cluster (bunkers + AA/SAM ring) ---
    spawn_bunker_cluster()







def spawn_bunker_cluster():
    # One guarded cluster: 3–5 bunkers + ring of AA/SAM; place on mountain/valley/flat randomly
    cnt = random.randint(*BUNKER_COUNT)
    cx,cy = _rand_xy(min(PLACEMENT_RADIUS*0.8, PLAY_EXTENT*0.6))
    cluster_id = random.randint(1000,9999)
    # bunkers
    for i in range(cnt):
        dx = math.cos(i*math.tau/cnt)*600.0
        dy = math.sin(i*math.tau/cnt)*600.0
        x,y = cx+dx, cy+dy
        bunkers.append({'id': _new_gid(), 'class':'BUNKER', 'p':[x,y], 'z':terrain_h(x,y),
                'cluster_id':cluster_id, 'hp':220, 'hp_max':220})

    # defense ring: AA and a few SAMs
    ring = []
    for th in (0, .4, .8, 1.2, 1.6, 2.0):
        r = 1400.0 + random.uniform(-200, 300)
        x = cx + math.cos(th*math.pi)*r
        y = cy + math.sin(th*math.pi)*r
        ring.append((x,y))
    for i,(x,y) in enumerate(ring):
        if i % 3 == 0:
            sam_units.append({'id': _new_gid(), 'class':'SAM',
                            'p':[x,y], 'z':terrain_h(x,y),
                            'hp':160, 'hp_max':160, 'cool':0.0,
                            'loaded': True, 'aiming': False})
        else:
            aa_units.append({'id': _new_gid(), 'class':'AA',
                            'p':[x,y], 'z':terrain_h(x,y),
                            'hp':100, 'hp_max':100, 'cool':0.0})















# ---------------- Jet ----------------
def draw_f117(elevonL_deg=0.0, elevonR_deg=0.0, rudder_deg_vis=0.0):
    # debug palette
    def dbg_color(i):
        pal = [(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,0,1),(0,1,1),
               (0.9,0.5,0.1),(0.5,0.9,0.1),(0.1,0.9,0.5),
               (0.9,0.1,0.5),(0.5,0.1,0.9),(0.3,0.7,0.9),
               (0.7,0.3,0.9),(0.9,0.7,0.3),(0.3,0.9,0.7)]
        return pal[i % len(pal)]

    # vertices
    V = {
        "N":(120,0,4), "CL":(100,-28,12), "CR":(100,28,12),
        "R1":(60,0,30), "R2":(36,0,27), "CNL":(46,-12,28.5), "CNR":(46,12,28.5),
        "WRL":(8,-72,7), "WRR":(8,72,7), "WTL":(-170,-210,0), "WTR":(-170,210,0),
        "TIL":(-100,-48,5), "TIR":(-100,48,5), "EOL":(-150,-170,2), "EOR":(-150,170,2),
        "ADL":(-108,-34,6.6), "ADR":(-108,34,6.6),
        "AT1L":(-124,-22,4.2), "AT1R":(-124,22,4.2), "V_TOP":(-146,0,2.1),
        "BAL":(-94,-40,-4), "BAR":(-94,40,-4), "AB1L":(-120,-12,-0.8), "AB1R":(-120,12,-0.8),
        "V_BOT":(-146,0,0), "ADC":(-118,0,5), "AFTB":(-122,0,-2),
        "CHIN":(38,0,-16), "BML":(4,-58,-6), "BMR":(4,58,-6),
        "TOPC":(-12,0,18)
    }
    for k,(x,y,z) in list(V.items()):
        V[k] = (x, y*0.70, z)

    # Build V-tail quads from seam TOPC-ADC
    H0 = V["TOPC"]; H1 = V["ADC"]
    L0 = v_lerp(H0,H1,0.99); L1 = v_lerp(H0,H1,0.90)
    aft, up, out = -26.0, 34.0, 14.0
    LT2 = v_add(L1,(aft,-out,up));  LT3 = v_add(L0,(aft,-out,up))
    RT2 = v_add(L1,(aft, out,up));  RT3 = v_add(L0,(aft, out,up))
    V.update({"VT_L0":L0,"VT_L1":L1,"VT_L2":LT2,"VT_L3":LT3,
              "VT_R0":L0,"VT_R1":L1,"VT_R2":RT2,"VT_R3":RT3})

    faces = []
    tail_quads = [("VT_L0","VT_L1","VT_L2","VT_L3"),
                  ("VT_R0","VT_R1","VT_R2","VT_R3")]

    # Nose/canopy
    faces += [("N","CL","R1"),("N","R1","CR"),
              ("CL","WRL","R1"),("CR","R1","WRR"),
              ("R1","CNL","R2"),("R1","R2","CNR")]
    # Top deck
    faces += [("R2","WRL","TOPC"),("R2","TOPC","WRR"),
              ("WRL","TIL","TOPC"),("WRR","TOPC","TIR"),
              ("TOPC","TIL","ADC"),("TOPC","ADC","TIR")]
    # Cheeks
    faces += [("WRL","R1","CNL"),
              ("WRL","CNL","R2"),
              ("WRR","CNR","R1"),
              ("WRR","R2","CNR")]
    # Wing tops
    faces += [("WRL","EOL","TIL"),
              ("WRR","TIR","EOR")]
    # Side walls
    faces += [("CL","WRL","BML"),("CL","BML","CHIN"),
              ("CR","BMR","WRR"),("CR","CHIN","BMR"),
              ("WRL","TIL","BAL"),("WRL","BAL","BML"),
              ("WRR","BAR","TIR"),("WRR","BMR","BAR")]
    # Belly
    faces += [("N","CR","CHIN"),("N","CHIN","CL"),
              ("CHIN","BML","BMR"),("BML","AFTB","BMR"),
              ("AFTB","BML","BAL"),("AFTB","BAR","BMR")]
    # Exhaust
    faces += [("TIL","ADC","BAL"),("ADC","AFTB","BAL"),
              ("ADC","TIR","BAR"),("ADC","BAR","AFTB")]

    # Baked materials
    JET_DARK  = (0.08,0.08,0.09)
    JET_BASE2 = (0.10,0.10,0.11)
    JET_LIGHT = (0.16,0.16,0.17)
    WIN_COLOR = (0.75,0.85,1.00)
    EXH_COLOR = (0.45,0.22,0.22)
    FLAP_COLOR = (0.86,0.87,0.89)  # greyish white

    WINDOWS = {("WRR","CNR","R1"), ("WRL","R1","CNL")}
    EXHAUST = {
        ("TIL","ADC","BAL"), ("ADC","AFTB","BAL"),
        ("ADC","TIR","BAR"), ("ADC","BAR","AFTB"),
    }

    WING_TOPS   = {("WRL","EOL","TIL"), ("WRR","TIR","EOR")}
    NOSE_BLOCK  = {("N","CL","R1"), ("N","R1","CR")}
    TOP_DECK    = {
        ("R2","WRL","TOPC"),("R2","TOPC","WRR"),
        ("WRL","TIL","TOPC"),("WRR","TOPC","TIR"),
        ("TOPC","TIL","ADC"),("TOPC","ADC","TIR"),
    }
    CHEEKS = {("WRL","R1","CNL"), ("WRR","CNR","R1")}
    SIDEWALLS = {
        ("CL","WRL","BML"),("CL","BML","CHIN"),
        ("CR","BMR","WRR"),("CR","CHIN","BMR"),
        ("WRL","TIL","BAL"),("WRL","BAL","BML"),
        ("WRR","BAR","TIR"),("WRR","BMR","BAR"),
    }
    BELLY = {
        ("N","CR","CHIN"),("N","CHIN","CL"),
        ("CHIN","BML","BMR"),("BML","AFTB","BMR"),
        ("AFTB","BML","BAL"),("AFTB","BAR","BMR"),
    }

    def _panel_base(name3):
        if name3 in WINDOWS: return WIN_COLOR
        if name3 in EXHAUST: return EXH_COLOR
        if name3 in WING_TOPS:  return JET_LIGHT
        if name3 in TOP_DECK:   return (0.12,0.12,0.13)
        if name3 in NOSE_BLOCK: return (0.12,0.12,0.13)
        if name3 in CHEEKS:     return (0.13,0.13,0.14)
        if name3 in SIDEWALLS:  return JET_DARK
        if name3 in BELLY:      return (0.06,0.06,0.07)
        return JET_BASE2

    def _jitter(name3, rgb):
        h = hash(name3) & 0xffff
        s = (h % 9 - 4) * 0.005
        return (max(0.0, min(1.0, rgb[0]+s)),
                max(0.0, min(1.0, rgb[1]+s)),
                max(0.0, min(1.0, rgb[2]+s)))

    # drawing helpers
    def tri_dev(a,b,c,idx):
        glColor3f(*dbg_color(idx))
        glVertex3f(*a); glVertex3f(*b); glVertex3f(*c)

    def tri_std(a,b,c,idx,name3):
        base = _panel_base(name3)
        if name3 in WINDOWS or name3 in EXHAUST:
            glColor3f(*base)  # flat
        else:
            glColor3f(*_jitter(name3, base))
        glVertex3f(*a); glVertex3f(*b); glVertex3f(*c)

    # flap primitives
    def draw_flap_strip_tri(opposite, e0, e1, width_t, defl_deg):
        """Create a thin quad strip along edge e0-e1 inside triangle (opposite,e0,e1),
        hinged along the inner line at 'width_t' from the edge; rotate free edge about hinge."""
        H0 = v_lerp(opposite, e0, width_t)
        H1 = v_lerp(opposite, e1, width_t)
        F0 = e0
        F1 = e1
        # Rotate free edge points about hinge axis
        F0r = rotate_around_axis(F0, H0, H1, defl_deg)
        F1r = rotate_around_axis(F1, H0, H1, defl_deg)
        glBegin(GL_QUADS)
        glColor3f(*FLAP_COLOR)
        glVertex3f(*H0); glVertex3f(*H1); glVertex3f(*F1r); glVertex3f(*F0r)
        glEnd()

    def draw_flap_strip_quad(q0,q1,q2,q3, width_t, defl_deg):
        """Quad with order (q0,q1,q2,q3). We form a strip near the trailing edge q3-q2 (parallel).
        Hinge line at width_t from q3-q2 toward q0-q1."""
        # interpolate along the two side edges toward trailing edge
        H0 = v_lerp(q0, q3, width_t)
        H1 = v_lerp(q1, q2, width_t)
        F0 = q3; F1 = q2  # trailing edge
        F0r = rotate_around_axis(F0, H0, H1, defl_deg)
        F1r = rotate_around_axis(F1, H0, H1, defl_deg)
        # offset along quad normal
        n = tri_normal(q0, q1, q2)
        eps = 0.6
        H0 = offset_point_along_normal(H0, n, eps)
        H1 = offset_point_along_normal(H1, n, eps)
        F0r = offset_point_along_normal(F0r, n, eps)
        F1r = offset_point_along_normal(F1r, n, eps)
        glBegin(GL_QUADS)
        glColor3f(*FLAP_COLOR)
        glVertex3f(*H0); glVertex3f(*H1); glVertex3f(*F1r); glVertex3f(*F0r)
        glEnd()

    # --- draw hull ---
    glPushMatrix()
    was_cull = glIsEnabled(GL_CULL_FACE)
    glDisable(GL_LIGHTING)
    if was_cull: glDisable(GL_CULL_FACE)

    glTranslatef(pos[0], pos[1], pos[2])
    glRotatef(yaw_deg,0,0,1); glRotatef(-pitch_deg,0,1,0); glRotatef(roll_deg,1,0,0)

    glBegin(GL_TRIANGLES)
    for i,(a,b,c) in enumerate(faces):
        if dev_colors: tri_dev(V[a],V[b],V[c],i)
        else:          tri_std(V[a],V[b],V[c],i,(a,b,c))
    glEnd()

    # V-tail quads (base surface)
    glBegin(GL_QUADS)
    base_idx = len(faces)
    for j,(a,b,c,d) in enumerate(tail_quads):
        if dev_colors:
            glColor3f(*dbg_color(base_idx+j))
        else:
            glColor3f(0.14,0.14,0.15)
        glVertex3f(*V[a]); glVertex3f(*V[b]); glVertex3f(*V[c]); glVertex3f(*V[d])
    glEnd()

    # ---------------- Flaps (ambient, slim, grey-white) ----------------
    if not dev_colors:
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(-2.0, -2.0)
        # --- Wing elevons ---
        width_t = 0.93  # how close to trailing edge (slim)
        # left wing triangle: ("WRL","EOL","TIL") -> trailing edge = (EOL,TIL); opposite = WRL
        opp = V["WRL"]; e_out = V["EOL"]; e_in = V["TIL"]
        # split into outboard and inboard halves along the hinge
        mid = v_lerp(e_out, e_in, 0.5)
        # Outboard strip (EOL to mid)
        draw_flap_strip_tri(opp, e_out, mid, width_t, defl_deg = clamp(elevonL_deg*0.6 + (+elevonL_deg - elevonR_deg)*0.5, -ELV_MAX, ELV_MAX))
        # Inboard strip (mid to TIL)
        draw_flap_strip_tri(opp, mid, e_in, width_t, defl_deg = clamp(elevonL_deg*1.0 + (+elevonL_deg - elevonR_deg)*0.2, -ELV_MAX, ELV_MAX))

        # right wing triangle: ("WRR","TIR","EOR") -> trailing edge = (TIR,EOR); opposite = WRR
        opp = V["WRR"]; e_in = V["TIR"]; e_out = V["EOR"]
        mid = v_lerp(e_in, e_out, 0.5)
        # Inboard strip (TIR to mid)
        draw_flap_strip_tri(opp, e_in, mid, width_t, defl_deg = clamp(elevonR_deg*1.0 + (elevonR_deg - elevonL_deg)*0.2, -ELV_MAX, ELV_MAX))
        # Outboard strip (mid to EOR)
        draw_flap_strip_tri(opp, mid, e_out, width_t, defl_deg = clamp(elevonR_deg*0.6 + (elevonR_deg - elevonL_deg)*0.5, -ELV_MAX, ELV_MAX))

        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(-2.0, -2.0)
        # --- Tail rudders (one slim strip on each V-tail trailing edge) ---
        width_t_tail = 0.86
        # Left tail quad order: ("VT_L0","VT_L1","VT_L2","VT_L3")  -> trailing edge q3-q2
        draw_flap_strip_quad(V["VT_L0"],V["VT_L1"],V["VT_L2"],V["VT_L3"], width_t_tail, defl_deg = +rudder_deg_vis)
        # Right tail
        draw_flap_strip_quad(V["VT_R0"],V["VT_R1"],V["VT_R2"],V["VT_R3"], width_t_tail, defl_deg = -rudder_deg_vis)

        glDisable(GL_POLYGON_OFFSET_FILL)
        # --- Edge ink overlay for clarity ---
        glEnable(GL_POLYGON_OFFSET_LINE); glPolygonOffset(-1.0, -1.0)
        glLineWidth(1.2); glColor3f(0.03,0.03,0.04)
        glBegin(GL_LINES)
        drawn=set()
        for a,b,c in faces:
            for e in [(a,b),(b,c),(c,a)]:
                key=tuple(sorted(e))
                if key in drawn: continue
                drawn.add(key)
                va,vb = V[e[0]], V[e[1]]
                glVertex3f(*va); glVertex3f(*vb)
        for a,b,c,d in tail_quads:
            for e in [(a,b),(b,c),(c,d),(d,a)]:
                key=tuple(sorted(e))
                if key in drawn: continue
                drawn.add(key); va,vb=V[e[0]],V[e[1]]
                glVertex3f(*va); glVertex3f(*vb)
        glEnd()
        glDisable(GL_POLYGON_OFFSET_LINE)

    if was_cull: glEnable(GL_CULL_FACE)
    glPopMatrix()

# ---------------- Weapons ----------------
def spawn_bullet():
    (fx,fy,fz), _, _ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)
    nose_offset = 90.0
    start = [pos[0] + fx*nose_offset,
             pos[1] + fy*nose_offset,
             pos[2] + fz*nose_offset]
    vel = [fx*BULLET_SPEED, fy*BULLET_SPEED, fz*BULLET_SPEED]
    bullets.append({'p': start, 'v': vel, 't0': time.time()})

def update_bullets(dt):
    if not bullets: return
    now = time.time()
    keep = []
    limit = RADAR_RANGE * 1.1   # bullets vanish once beyond radar coverage

    for b in bullets:
        # integrate
        b['p'][0] += b['v'][0]*dt
        b['p'][1] += b['v'][1]*dt
        b['p'][2] += b['v'][2]*dt

        # lifetime
        alive = (now - b['t0']) < BULLET_LIFE

        # player-relative, circular cull (NOT origin-relative box)
        dx = b['p'][0] - pos[0]
        dy = b['p'][1] - pos[1]
        dist2 = dx*dx + dy*dy
        in_range = (dist2 <= (limit*limit)) and (0.0 < b['p'][2] < PLAYER_ALT_MAX + 1000.0)

        # ground collisions
        if _bullet_hit_any_ground(b):
            b['t0'] = 0.0  # retire on first ground hit
            continue

        if alive and in_range:

            keep.append(b)
    bullets[:] = keep

# --- Player fire cadence ---
def player_fire_update(dt, keys_down):
    if not hasattr(player_fire_update, "hold"):
        player_fire_update.hold  = False
        player_fire_update.accum = 0.0
        player_fire_update.rate  = 12.0
    if b' ' in keys_down:
        player_fire_update.hold = True
    else:
        player_fire_update.hold = False
        player_fire_update.accum = 0.0
        return
    if player_fire_update.hold:
        player_fire_update.accum += dt * player_fire_update.rate
        while player_fire_update.accum >= 1.0:
            spawn_bullet(); player_fire_update.accum -= 1.0

# ---------------- Simulation ----------------



def update_lock(dt):
    """Locks air + ground depending on missile:
       - A2A_* : AIR + TAA
       - A2S_G : TAA + AA + SAM + BUNKER
    """
    global _target_id, _lock_timer, _lock_state
    m = MISSILES[MSL_SELECTED]
    cone = m['lock_cone_deg']

    allow = []
    if MSL_SELECTED in ('A2A_S','A2A_M'):
        allow = ['AIR','TAA']
    else:  # A2S
        allow = ['TAA','AA','SAM','BUNKER']

    # 1) cone-only candidates (range ignored to keep circle visible)
    cands = _front_cone_candidates_any(cone_deg=cone, max_range=None, allow=allow)
    if not cands:
        _target_id, _lock_timer, _lock_state = None, 0.0, 'NONE'
        return

    # 2) sticky target if still within slightly wider cone
    stick_ok = False
    if _target_id is not None:
        tp = _resolve_target_pos(_target_id)
        if tp:
            (fx,fy,fz),_,_ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)
            vx,vy,vz = tp[0]-pos[0], tp[1]-pos[1], tp[2]-pos[2]
            L = math.sqrt(vx*vx+vy*vy+vz*vz)+1e-9
            dp = (fx*vx + fy*vy + fz*vz)/L
            stick_ok = dp >= math.cos(math.radians(cone + STICK_CONE_EXTRA))

    # 3) choose target
    if not stick_ok:
        _target_id = cands[0][0]
        _lock_timer = 0.0
        _lock_state = 'ACQ'

    # 4) range/timer
    tp = _resolve_target_pos(_target_id)
    if not tp:
        _target_id, _lock_timer, _lock_state = None, 0.0, 'NONE'
        return
    dist = math.sqrt((tp[0]-pos[0])**2 + (tp[1]-pos[1])**2 + (tp[2]-pos[2])**2)
    if dist > m['lock_range']:
        _lock_state = 'OUT'
        _lock_timer = 0.0
        return

    if _lock_state != 'LOCK':
        _lock_state = 'ACQ'
        _lock_timer += dt
        if _lock_timer >= m['lock_time']:
            _lock_state = 'LOCK'






def update(dt):
    global yaw_deg, pitch_deg, roll_deg, roll_cmd, speed, pos, rudder_cmd, rudder_deg

    # yaw rate scales with speed
    yawrate = yaw_rate_for_speed()

    # Helper: locked key
    def _is_down(k):
        return (k in keys_down) or (lock_active and locked_key == k)

    # A/D yaw; W/S pitch
    turn_left = _is_down(b'a')
    turn_right= _is_down(b'd')
    if turn_left:  yaw_deg += yawrate * dt
    if turn_right: yaw_deg -= yawrate * dt
    if _is_down(b'w'): pitch_deg += PITCH_RATE * dt
    if _is_down(b's'): pitch_deg -= PITCH_RATE * dt
    pitch_deg = clamp(pitch_deg, -85.0, 85.0)

    # Rudder command follows key intent (visual only)
    target = 0.0
    if turn_left and not turn_right:  target = +RUDDER_MAX
    if turn_right and not turn_left:  target = -RUDDER_MAX
    # smooth to target
    if   rudder_deg < target: rudder_deg = min(target, rudder_deg + RUDDER_TRACK*dt)
    elif rudder_deg > target: rudder_deg = max(target, rudder_deg - RUDDER_TRACK*dt)
    rudder_cmd = target  # exposed if needed

    # Speed
    if (b'r' in keys_down) or (b'R' in keys_down): speed = clamp(speed + SPEED_STEP, SPEED_MIN, SPEED_MAX)
    if (b'f' in keys_down) or (b'F' in keys_down): speed = clamp(speed - SPEED_STEP, SPEED_MIN, SPEED_MAX)

    # Q/E bank
    qe_left  = _is_down(b'q')
    qe_right = _is_down(b'e')
    if   qe_left and not qe_right:  roll_cmd = clamp(roll_cmd - ROLL_CMD_RATE * dt, -ROLL_MAX_DEG, ROLL_MAX_DEG)
    elif qe_right and not qe_left:  roll_cmd = clamp(roll_cmd + ROLL_CMD_RATE * dt, -ROLL_MAX_DEG, ROLL_MAX_DEG)
    else:
        if   roll_cmd > 0: roll_cmd = max(0.0, roll_cmd - ROLL_AUTOCENTER * dt)
        elif roll_cmd < 0: roll_cmd = min(0.0, roll_cmd + ROLL_AUTOCENTER * dt)

    # Track bank
    if   roll_deg < roll_cmd: roll_deg = min(roll_cmd, roll_deg + ROLL_TRACK_RATE * dt)
    elif roll_deg > roll_cmd: roll_deg = max(roll_cmd, roll_deg - ROLL_TRACK_RATE * dt)

    # Advance
    (fx,fy,fz), _, _ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)
    pos[0] += fx * speed * dt; pos[1] += fy * speed * dt; pos[2] += fz * speed * dt


    # --- SIMPLE GROUND COLLISION -> instant respawn (unless invincible) ---
    gz = max(terrain_h(pos[0], pos[1]), GROUND_PLANE_Z)  # real terrain (or flat plane)
    if not PLAYER_INVINCIBLE and (pos[2] - PLAYER_HULL_CLEARANCE) <= gz:
        try:
            spawn_explosion([pos[0], pos[1], gz + 10.0], base_radius=160.0, ttl=0.7, kind='terrain')
        except Exception:
            pass
        reset_player()
        return  # stop this frame; we've respawned


    resolve_player_collisions(dt)




    # Lateral drift while Q/E held (yaw/pitch forward)
    cy, sy = math.cos(deg2rad(yaw_deg)), math.sin(deg2rad(yaw_deg))
    cp, sp = math.cos(deg2rad(pitch_deg)), math.sin(deg2rad(pitch_deg))
    fx_np, fy_np, fz_np = cy*cp, sy*cp, sp
    rx, ry =  fy_np, -fx_np
    rlen = math.hypot(rx, ry) + 1e-9; r_hx, r_hy = rx/rlen, ry/rlen
    if qe_left and not qe_right:
        k = BANK_DRIFT_RATIO * speed; pos[0] -= r_hx*k*dt; pos[1] -= r_hy*k*dt
    if qe_right and not qe_left:
        k = BANK_DRIFT_RATIO * speed; pos[0] += r_hx*k*dt; pos[1] += r_hy*k*dt

    if pos[2] < 10.0: pos[2] = 10.0
    if abs(yaw_deg) >= 360.0: yaw_deg = math.fmod(yaw_deg, 360.0)

    # keep player within the vast world bounds horizontally
    pos[0] = clamp(pos[0], -GROUND_EXTENT*0.999, GROUND_EXTENT*0.999)
    pos[1] = clamp(pos[1], -GROUND_EXTENT*0.999, GROUND_EXTENT*0.999)
    # Altitude limits
    pos[2] = clamp(pos[2], PLAYER_ALT_MIN, PLAYER_ALT_MAX)








    player_fire_update(dt, keys_down); update_bullets(dt); update_enemies(dt)



    update_flares(dt)





    update_lock(dt)
    update_missiles(dt)  # update missiles after lock logic

    update_ground_weapons(dt)
    update_sams(dt)

    update_aa_shots(dt)

    _prune_dead_ground()


    update_world(dt)

    update_explosions(dt)













# ---------------- HUD/Camera ----------------
def draw_bullets():
    glDisable(GL_LIGHTING); glColor3f(1.0, 0.95, 0.25); glPointSize(6.0)
    glBegin(GL_POINTS)
    for b in bullets: glVertex3f(*b['p'])
    glEnd()














def draw_radar():
    # panel box
    sz, pad = RADAR_SIZE, RADAR_PADDING
    x0, y0 = WIN_W - sz - pad, WIN_H - sz - pad
    x1, y1 = x0 + sz, y0 + sz
    cx, cy = (x0 + x1)*0.5, (y0 + y1)*0.5
    half   = sz*0.5
    scale  = half / RADAR_RANGE

    # facing vectors from yaw (radar rotates with player)
    fx = math.cos(deg2rad(yaw_deg)); fy = math.sin(deg2rad(yaw_deg))
    rx, ry = +fy, -fx

    # background disc
    glLineWidth(1.0)
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(0.05,0.05,0.08,RADAR_ALPHA)
    seg = 48
    glBegin(GL_TRIANGLE_FAN); glVertex2f(cx,cy)
    for i in range(seg+1):
        th = 2.0*math.pi*i/seg
        glVertex2f(cx+half*math.cos(th), cy+half*math.sin(th))
    glEnd()
    # border
    glColor3f(0.15,0.15,0.20)
    glBegin(GL_LINE_LOOP)
    for i in range(seg):
        th = 2.0*math.pi*i/seg
        glVertex2f(cx+half*math.cos(th), cy+half*math.sin(th))
    glEnd()

    def _to_radar(px,py):
        dx=px-pos[0]; dy=py-pos[1]
        lx = dx*rx + dy*ry
        ly = dx*fx + dy*fy
        return (cx + lx*scale, cy + ly*scale)
    
    # bullet-shaped 2D outline (for SAM/A2S missiles on radar)
    def _icon_bullet(px, py, s, col_rgba=(1,1,1,1)):
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(col_rgba[0], col_rgba[1], col_rgba[2], col_rgba[3])
        glLineWidth(1.4)

        w = s * 0.50   # half-width of body
        h = s * 0.90   # total height (tip to base)

        # body rectangle (centered)
        bh = h * 0.45
        glBegin(GL_LINE_LOOP)
        glVertex2f(px - w, py - bh)
        glVertex2f(px + w, py - bh)
        glVertex2f(px + w, py + bh)
        glVertex2f(px - w, py + bh)
        glEnd()

        # nose triangle (points "up" in the radar panel)
        glBegin(GL_LINE_LOOP)
        glVertex2f(px,     py + h*0.95)
        glVertex2f(px + w, py + bh)
        glVertex2f(px - w, py + bh)
        glEnd()

        # base bands
        glBegin(GL_LINES)
        glVertex2f(px - w, py - bh - 2.0); glVertex2f(px + w, py - bh - 2.0)
        glVertex2f(px - w, py - bh - 5.0); glVertex2f(px + w, py - bh - 5.0)
        glEnd()

        glLineWidth(1.0)
        glDisable(GL_BLEND)


    # quadrant cross + range ticks + N/E/S/W labels
    glColor3f(0.18,0.85,0.22)
    glBegin(GL_LINES)
    glVertex2f(cx-half, cy); glVertex2f(cx+half, cy)   # horizontal
    glVertex2f(cx, cy-half); glVertex2f(cx, cy+half)   # vertical
    glEnd()
    # ticks on the cross (perpendicular marks)
    for k in range(1, RADAR_TICK_STEPS+1):
        r = half * (k / float(RADAR_TICK_STEPS))
        t = 6.0  # tick length
        # horizontal line ticks
        glBegin(GL_LINES)
        glVertex2f(cx - r, cy - t*0.5); glVertex2f(cx - r, cy + t*0.5)
        glVertex2f(cx + r, cy - t*0.5); glVertex2f(cx + r, cy + t*0.5)
        glEnd()
        # vertical line ticks
        glBegin(GL_LINES)
        glVertex2f(cx - t*0.5, cy - r); glVertex2f(cx + t*0.5, cy - r)
        glVertex2f(cx - t*0.5, cy + r); glVertex2f(cx + t*0.5, cy + r)
        glEnd()
    # N/E/S/W letters (compass-ish)
    # Static panel compass labels (do not rotate with player)
    # Revolving N/E/S/W labels (rotate with world; head-up radar)
    a0 = -math.radians(yaw_deg)              # world->panel rotation
    r_label = half - 12.0
    def _cardinal(deg, txt):
        th = a0 + math.radians(deg)
        lx = cx + r_label * math.sin(th)
        ly = cy + r_label * math.cos(th)
        draw_screen_text(lx - 5, ly - 6, txt, color=(0.8,1.0,0.8))
    for deg, txt in ((0,'N'), (90,'E'), (180,'S'), (270,'W')):
        _cardinal(deg, txt)

    # Tiny north arrow (still helpful)
    nx = cx + r_label * math.sin(a0)
    ny = cy + r_label * math.cos(a0)
    glColor3f(0.9, 0.95, 0.9)
    glBegin(GL_LINES)
    glVertex2f(nx, ny)
    glVertex2f(nx - 10.0*math.sin(a0), ny - 10.0*math.cos(a0))
    glEnd()



    # visual-range ring
    glColor3f(0.22,0.9,0.22)
    r_vis = half * (VISUAL_RANGE / RADAR_RANGE)
    glBegin(GL_LINE_LOOP)
    for i in range(seg):
        th=2.0*math.pi*i/seg
        glVertex2f(cx+r_vis*math.cos(th), cy+r_vis*math.sin(th))
    glEnd()

    # ---------------- Dots / rings ----------------

    # enemies (aircraft): red dots
    glPointSize(ENEMY_DOT_SIZE)
    glBegin(GL_POINTS)
    for e in enemies:
        dx=e['p'][0]-pos[0]; dy=e['p'][1]-pos[1]
        if math.hypot(dx,dy) > RADAR_RANGE: 
            continue
        px,py = _to_radar(e['p'][0],e['p'][1])
        if (px-cx)**2+(py-cy)**2 > (half-2.0)**2: 
            continue
        glColor3f(1.0,0.12,0.12)
        glVertex2f(px,py)
    glEnd()

    # towers: big filled circle + ONE ring:
    #  - FRIEND: blue "no fire on me" bubble (TOWER_NOFIRE_R)
    #  - FOE   : red tower-AA reach (TOWER_AA_RANGE)
    for i,t in enumerate(towers):
        px,py = _to_radar(t['p'][0],t['p'][1])
        if (px-cx)**2+(py-cy)**2 > (half-2.0)**2: 
            continue
        # dot
        glPointSize(TOWER_DOT_SIZE)
        glBegin(GL_POINTS)
        if t['faction']==FACTION_FRIEND: glColor3f(0.20,0.60,1.0)
        else:                            glColor3f(1.0,0.20,0.20)
        glVertex2f(px,py)
        glEnd()
        # ring
        if t['faction']==FACTION_FRIEND:
            glColor4f(0.2,0.6,1.0,0.30)
            r = TOWER_NOFIRE_R * scale
        else:
            glColor4f(1.0,0.3,0.25,0.22)
            r = TOWER_AA_RANGE * scale
        glBegin(GL_LINE_LOOP)
        for i2 in range(36):
            th=2.0*math.pi*i2/36
            glVertex2f(px+r*math.cos(th), py+r*math.sin(th))
        glEnd()

    # scattered AA: light-red cross + small red circle = its effective bullet reach
    for u in aa_units:
        px,py=_to_radar(u['p'][0],u['p'][1])
        if (px-cx)**2+(py-cy)**2 > (half-2.0)**2: 
            continue
        # cross mark
        s = 4.0
        glColor3f(1.0,0.45,0.45)
        glBegin(GL_LINES)
        glVertex2f(px-s,py); glVertex2f(px+s,py)
        glVertex2f(px,py-s); glVertex2f(px,py+s)
        glEnd()
        # short ring
        glColor4f(1.0,0.35,0.35,0.20)
        r = min(AA_RANGE_H, RADAR_RANGE) * scale
        glBegin(GL_LINE_LOOP)
        for i2 in range(24):
            th=2.0*math.pi*i2/24
            glVertex2f(px+r*math.cos(th), py+r*math.sin(th))
        glEnd()

    # SAM sites:
    #  - Yellow = inactive / reloading / not aiming
    #  - Red    = aiming AND loaded (hot)
    # Ring is clamped to radar edge and only drawn if the SAM itself is on radar.
    for u in sam_units:
        px,py=_to_radar(u['p'][0],u['p'][1])
        if (px-cx)**2+(py-cy)**2 > (half-2.0)**2: 
            continue
        hot = bool(u.get('aiming', False) and u.get('loaded', True))
        # dot
        glPointSize(4.0)
        glBegin(GL_POINTS)
        if hot: glColor3f(1.0,0.18,0.18)      # loaded & aiming
        else:  glColor3f(1.0,0.85,0.10)       # inactive / reloading
        glVertex2f(px,py)
        glEnd()
        # range ring (capped to radar)
        rcap = _radar_cap_range(SAM_RANGE) * scale
        glColor4f(*( (1.0,0.18,0.18,0.22) if hot else (1.0,0.85,0.10,0.22) ))
        glBegin(GL_LINE_LOOP)
        for i2 in range(36):
            th=2.0*math.pi*i2/36
            glVertex2f(px+rcap*math.cos(th), py+rcap*math.sin(th))
        glEnd()

    # bunkers: black square + small black hint circle (their local AA umbrella)
    for b in bunkers:
        px,py=_to_radar(b['p'][0],b['p'][1])
        if (px-cx)**2+(py-cy)**2 > (half-2.0)**2: 
            continue
        # square
        s = 4.5
        glColor3f(0.05,0.05,0.05)
        glBegin(GL_QUADS)
        glVertex2f(px-s,py-s); glVertex2f(px+s,py-s); glVertex2f(px+s,py+s); glVertex2f(px-s,py+s)
        glEnd()
        # small circle hint (visual)
        glColor4f(0.05,0.05,0.05,0.22)
        r = min(BUNKER_AA_HINT_R, RADAR_RANGE) * scale
        glBegin(GL_LINE_LOOP)
        for i2 in range(24):
            th=2.0*math.pi*i2/24
            glVertex2f(px+r*math.cos(th), py+r*math.sin(th))
        glEnd()

    
        # --- missiles on radar (IR chevron, A2A arrow, SAM/A2S bullet) ---
    for m in missiles:
        # screen position on radar disc
        px, py = _to_radar(m['pos'][0], m['pos'][1])
        if (px - cx)**2 + (py - cy)**2 > (half - 2.0)**2:
            continue

        # colors: hostile (targeting player) = red; ours = cyan/amber by kind
        if m.get('target_player'):
            col = (1.0, 0.35, 0.35, 0.95)
        else:
            col = (1.0, 0.68, 0.22, 0.95) if m.get('kind') == 'IR' else (0.30, 0.90, 1.00, 0.95)

        if m.get('kind') == 'IR':
            # chevron (open V) for IR
            s = 8.0
            glColor4f(*col)
            glBegin(GL_LINES)
            glVertex2f(px - s, py - s); glVertex2f(px,     py + s*0.9)
            glVertex2f(px + s, py - s); glVertex2f(px,     py + s*0.9)
            glEnd()
        elif m.get('model') in ('ammo', 'round'):
            # SAM & A2S bullet/capsule outline
            _icon_bullet(px, py, 10.0, col_rgba=col)
        else:
            # simple arrow head for radar-guided A2A
            s = 8.0
            glColor4f(*col)
            glBegin(GL_TRIANGLES)
            glVertex2f(px,          py + s)
            glVertex2f(px - s*0.6,  py - s*0.6)
            glVertex2f(px + s*0.6,  py - s*0.6)
            glEnd()









    # missiles on radar (cyan=ours, red=hostile SAM)
    for m in missiles:
        px,py = _to_radar(m['pos'][0], m['pos'][1])
        if (px-cx)**2 + (py-cy)**2 > (half-2.0)**2:
            continue

        col = (1.0, 0.25, 0.25, 1.0) if m.get('target_player') else (0.3, 0.9, 1.0, 1.0)
        #is_ammo = (m.get('model') == 'ammo') or (m.get('kind') in ('RADAR', 'A2S'))
        is_ammo = (m.get('model') in ('ammo','round')) or (m.get('key') in ('A2S_G','SAM'))

        if is_ammo:
            _icon_bullet(px, py, 10.0, col)
        else:
            glColor3f(col[0], col[1], col[2])
            glPointSize(MISSILE_DOT_SIZE)
            glBegin(GL_POINTS); glVertex2f(px, py); glEnd()

            

        # heading tick (kept)
        glColor3f(0.9,0.1,0.1)
        glBegin(GL_LINES); glVertex2f(cx, y1-10); glVertex2f(cx, y1-2); glEnd()
        glDisable(GL_BLEND)


def draw_legend_overlay():
    """Slide-in legend panel from the left; shows radar icons, colors, and 2D missile shapes."""
    _hud_begin()

    # --- animate slide ---
    now = time.time()
    if legend_anim['t_prev'] == 0.0:
        legend_anim['t_prev'] = now
    dt = now - legend_anim['t_prev']
    legend_anim['t_prev'] = now

    x = legend_anim['x']
    tgt = legend_anim['target']
    spd = legend_anim['speed']
    if abs(x - tgt) > 0.5:
        step = spd * dt
        if x < tgt:
            x = min(tgt, x + step)
        else:
            x = max(tgt, x - step)
        legend_anim['x'] = x
    else:
        legend_anim['x'] = tgt
        x = tgt

    # fully hidden? exit quick
    if x <= -(LEGEND_W + 24.0) and not SHOW_LEGEND:
        _hud_end(); return

    # --- panel rect (top-left corner) ---
    px = x + 16.0
    py = 16.0
    w  = LEGEND_W
    h  = LEGEND_H

    # background
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(*LEGEND_BG)
    glBegin(GL_QUADS)
    glVertex2f(px, py); glVertex2f(px+w, py)
    glVertex2f(px+w, py+h); glVertex2f(px, py+h)
    glEnd()
    glDisable(GL_BLEND)

    # section title
    draw_screen_text(px + LEGEND_PAD, py + h - 20, "LEGEND", color=(0.95,0.95,1.0))

    # helpers to draw tiny HUD icons
    def _dot(cx, cy, size, col):
        glColor3f(*col); glPointSize(size)
        glBegin(GL_POINTS); glVertex2f(cx, cy); glEnd()

    def _cross(cx, cy, s, col):
        glColor3f(*col); glLineWidth(1.5)
        glBegin(GL_LINES)
        glVertex2f(cx-s, cy); glVertex2f(cx+s, cy)
        glVertex2f(cx, cy-s); glVertex2f(cx, cy+s)
        glEnd(); glLineWidth(1.0)

    def _square(cx, cy, s, col):
        glColor3f(*col)
        glBegin(GL_QUADS)
        glVertex2f(cx-s, cy-s); glVertex2f(cx+s, cy-s)
        glVertex2f(cx+s, cy+s); glVertex2f(cx-s, cy+s)
        glEnd()

    def _ring(cx, cy, r, col, a=1.0, seg=24):
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(col[0], col[1], col[2], a)
        glBegin(GL_LINE_LOOP)
        for i in range(seg):
            th = 2.0*math.pi*i/seg
            glVertex2f(cx + r*math.cos(th), cy + r*math.sin(th))
        glEnd()
        glDisable(GL_BLEND)

    def _arrow(cx, cy, s, col):
        # slim A2A/hostile missile icon (triangle + tail)
        glColor3f(*col)
        glBegin(GL_TRIANGLES)
        glVertex2f(cx + s*0.9, cy)
        glVertex2f(cx - s*0.5, cy - s*0.5)
        glVertex2f(cx - s*0.5, cy + s*0.5)
        glEnd()
        glBegin(GL_LINES)
        glVertex2f(cx - s*0.7, cy); glVertex2f(cx - s*1.0, cy)
        glEnd()

    def _ammo(cx, cy, s, col):
        # fat A2S/SAM ammo: capsule body + tip
        glColor3f(*col)
        # body
        glBegin(GL_QUADS)
        glVertex2f(cx - s*0.9, cy - s*0.45)
        glVertex2f(cx + s*0.3, cy - s*0.45)
        glVertex2f(cx + s*0.3, cy + s*0.45)
        glVertex2f(cx - s*0.9, cy + s*0.45)
        glEnd()
        # nose
        glBegin(GL_TRIANGLES)
        glVertex2f(cx + s*0.3, cy)
        glVertex2f(cx + s*0.9, cy - s*0.45)
        glVertex2f(cx + s*0.9, cy + s*0.45)
        glEnd()

    # rows
    row = py + h - 44
    xL  = px + LEGEND_PAD + 12
    xT  = xL + 30
    dy  = 22

    # Radar symbols (colors align with your radar code)
    # Enemy aircraft
    _dot(xL, row, ENEMY_DOT_SIZE, (1.0,0.12,0.12))
    draw_screen_text(xT, row-6, "Enemy aircraft (red dot)", color=(0.95,0.95,0.95)); row -= dy

    # Tower friend / foe
    _dot(xL, row, TOWER_DOT_SIZE, (0.2,0.60,1.0)); _ring(xL, row, 11, (0.2,0.60,1.0), 0.35)
    draw_screen_text(xT, row-6, "Friendly Tower (blue dot + blue no-fire ring)", color=(0.9,0.9,1.0)); row -= dy
    _dot(xL, row, TOWER_DOT_SIZE, (1.0,0.20,0.20)); _ring(xL, row, 11, (1.0,0.30,0.25), 0.35)
    draw_screen_text(xT, row-6, "Hostile Tower (red dot + red AA ring)", color=(1.0,0.85,0.85)); row -= dy

    # AA unit
    _cross(xL, row, 7, (1.0,0.45,0.45)); _ring(xL, row, 9, (1.0,0.35,0.35), 0.25)
    draw_screen_text(xT, row-6, "AA gun (light red cross + small red ring)", color=(1.0,0.85,0.85)); row -= dy

    # SAM inactive / active (yellow vs red/orange)
    _ammo(xL, row, 8, (1.0,0.85,0.10)); _ring(xL, row, 12, (1.0,0.85,0.10), 0.28)
    draw_screen_text(xT, row-6, "SAM Inactive (yellow) + capped range ring", color=(1.0,1.0,0.8)); row -= dy
    _ammo(xL, row, 8, (1.0,0.18,0.18)); _ring(xL, row, 12, (1.0,0.18,0.18), 0.28)
    draw_screen_text(xT, row-6, "SAM Active/Loaded (red) + capped range ring", color=(1.0,0.9,0.9)); row -= dy

    # Bunker
    _square(xL, row, 6, (0.05,0.05,0.05)); _ring(xL, row, 7, (0.05,0.05,0.05), 0.25)
    draw_screen_text(xT, row-6, "Bunker (black square + small local AA hint)", color=(0.85,0.85,0.85)); row -= dy

    # Missiles (ours vs hostile; A2A arrow vs A2S fat ammo)
    _arrow(xL, row, 8, (0.3,0.9,1.0))
    draw_screen_text(xT, row-6, "Our missile (cyan arrow)", color=(0.85,0.95,1.0)); row -= dy
    _arrow(xL, row, 8, (1.0,0.25,0.25))
    draw_screen_text(xT, row-6, "Hostile missile (red arrow)", color=(1.0,0.9,0.9)); row -= dy
    _ammo(xL, row, 8, (0.85,0.85,0.9))
    draw_screen_text(xT, row-6, "A2S/SAM ammo shape (fat round)", color=(0.92,0.92,1.0)); row -= dy

    # Color pattern summary
    row -= 6
    draw_screen_text(xL, row-4, "Colors:", color=(0.95,0.95,1.0))
    row -= dy
    _square(xL, row, 5, (1.0,0.12,0.12)); draw_screen_text(xT, row-6, "Enemy", color=(1.0,0.85,0.85)); row -= dy
    _square(xL, row, 5, (0.2,0.60,1.0)); draw_screen_text(xT, row-6, "Friendly", color=(0.9,0.95,1.0)); row -= dy
    _square(xL, row, 5, (1.0,0.85,0.10)); draw_screen_text(xT, row-6, "Inactive / reloading", color=(1.0,1.0,0.8)); row -= dy
    _square(xL, row, 5, (1.0,0.35,0.35)); draw_screen_text(xT, row-6, "Active / dangerous", color=(1.0,0.9,0.9)); row -= dy

    _hud_end()







def _los_blocked_by_towers(a, b, pad=0.0, steps=64):
    """Return True if the segment a->b intersects any tower cylinder."""
    if not towers:
        return False
    ax, ay, az = a; bx, by, bz = b
    for s in range(1, steps):
        u = s / float(steps)
        x = ax + (bx - ax) * u
        y = ay + (by - ay) * u
        z = az + (bz - az) * u
        for t in towers:
            tx, ty = t['p'][0], t['p'][1]
            r = t.get('r', 40.0)            # fallback radius if not set
            h = t.get('h', 260.0)           # fallback height if not set
            # horizontal distance to tower center
            dx = x - tx; dy = y - ty
            if (dx*dx + dy*dy) <= (r + pad) * (r + pad):
                # within radius; check height band (ground to top)
                if 0.0 <= z - GROUND_PLANE_Z <= h:
                    return True
    return False

def has_line_of_sight_all(a, b, clearance=30.0):
    """LOS that combines terrain and tower occlusion."""
    if not has_line_of_sight(a, b, clearance=clearance):
        return False
    if _los_blocked_by_towers(a, b, pad=clearance*0.3):
        return False
    return True










def draw_target_highlight_and_stats():
   
 
   
    allow = ['AIR', 'TAA', 'AA', 'SAM', 'BUNKER']
    cands = _front_cone_candidates_any(cone_deg=AIM_CONE_DEG, max_range=None, allow=allow)
    if not cands:
        return

    tid = cands[0][0]

    world_p = _resolve_target_pos(tid)
    if not world_p:
        return

    # Terrain + tower LOS
    if not has_line_of_sight_all([pos[0], pos[1], pos[2]], world_p, clearance=30.0):
        return

    scr = _project_to_screen(world_p[0], world_p[1], world_p[2])
    if not scr:
        return
    sx, sy = scr

    # distance
    dist_m = int(math.sqrt((world_p[0]-pos[0])**2 + (world_p[1]-pos[1])**2 + (world_p[2]-pos[2])**2))

    # aircraft speed (smoothed)
    spd_txt = ""
    if isinstance(tid, tuple) and tid[0] == 'AIR':
        e = _enemy_by_id(tid[1])
        if e:
            if 'v_prev' not in e:
                e['v_prev'] = e['p'][:]
                e['spd']    = 0.0
            dx = e['p'][0] - e['v_prev'][0]
            dy = e['p'][1] - e['v_prev'][1]
            dz = e['p'][2] - e['v_prev'][2]
            inst = math.sqrt(dx*dx + dy*dy + dz*dz) * 60.0
            e['spd'] = 0.85*e['spd'] + 0.15*inst
            e['v_prev'] = e['p'][:]
            spd_txt = f" | {int(e['spd'])} u/s"

    # label (from helper that maps AIR/AA/SAM/BUNKER/TAA etc.)
    _, _, lbl = _hp_and_label_for_tid(tid)

    # green diamond + text (no HP bar here)
    _hud_begin()
    glColor4f(0.2, 1.0, 0.2, 0.75)
    s = 18.0
    glBegin(GL_LINE_LOOP)
    glVertex2f(sx,     sy - s)
    glVertex2f(sx + s, sy)
    glVertex2f(sx,     sy + s)
    glVertex2f(sx - s, sy)
    glEnd()



    # NEW: fetch label + HP and build text
    hp, hpmax, lbl = _hp_and_label_for_tid(tid)
    hp_txt = f"  |  HP {int(max(0, hp))}/{int(hpmax)}" if (hp is not None and hpmax is not None) else ""



    draw_screen_text(sx + 12, sy - 18, f"{lbl}  {dist_m} m{hp_txt}{spd_txt}", color=(0.1, 1.0, 0.1))

    _hud_end()











def draw_lock_hud():
    if cam_mode != 'first':
        return
    m = MISSILES[MSL_SELECTED]

    tgt_pos = _resolve_target_pos(_target_id) if _target_id else None

    def _draw_center_cone():
        _hud_begin()
        cx, cy = WIN_W*0.5, WIN_H*0.5
        aspect = (WIN_W/float(WIN_H)) if WIN_H else 1.0
        fovy   = FOV_Y_FIRST if cam_mode == 'first' else FOV_Y
        fovx   = 2.0*math.degrees(math.atan(math.tan(math.radians(fovy)*0.5)*aspect))
        r      = (WIN_W*0.5) * (math.tan(math.radians(m['lock_cone_deg'])) / math.tan(math.radians(fovx*0.5)))
        glColor3f(0.6, 1.0, 0.6)
        seg = 64
        glBegin(GL_LINE_LOOP)
        for i in range(seg):
            th = 2.0*math.pi*i/seg
            glVertex2f(cx + r*math.cos(th), cy + r*math.sin(th))
        glEnd()
        _hud_end()
        return r

    # No target or blocked LOS => just center cone
    if not tgt_pos:
        _draw_center_cone(); return
    if not has_line_of_sight_all([pos[0],pos[1],pos[2]], tgt_pos, clearance=30.0):
        _draw_center_cone(); return

    scr = _project_to_screen(tgt_pos[0], tgt_pos[1], tgt_pos[2])
    if not scr:
        return
    sx, sy = scr

    _draw_center_cone()

    _hud_begin()
    if _lock_state == 'LOCK':
        glLineWidth(2.5)
        glColor3f(1.0, 0.25, 0.25)  # red diamond when locked
        s = 20.0
        glBegin(GL_LINE_LOOP)
        glVertex2f(sx, sy - s); glVertex2f(sx + s, sy); glVertex2f(sx, sy + s); glVertex2f(sx - s, sy)
        glEnd()
        glLineWidth(1.0)
    else:
        # yellow circle in OUT, green in ACQ
        is_out = (_lock_state == 'OUT')
        glColor3f(0.95, 0.95, 0.45) if is_out else glColor3f(0.6, 1.0, 0.6)
        rr = 20.0; seg2 = 48
        glBegin(GL_LINE_LOOP)
        for i in range(seg2):
            th = 2.0*math.pi*i/seg2
            glVertex2f(sx + rr*math.cos(th), sy + rr*math.sin(th))
        glEnd()

        # progress arc only in ACQ
        # progress arc only in ACQ (circle → diamond)
        # progress arc only in ACQ (circle → diamond)
        if not is_out and 'lock_time' in m and m['lock_time'] > 0.0:
            prog = max(0.0, min(1.0, _lock_timer / float(m['lock_time'])))

            if prog > 0.0:
                steps = 64
                # At least 3 points so it actually draws on all drivers
                npts = max(3, int(steps * prog) + 1)

                # Draw the arc slightly OUTSIDE the base circle so it’s clearly visible
                rr_arc = rr + 2.0

                # Make it a bit thicker and explicitly green
                glLineWidth(3.0)
                glColor3f(0.6, 1.0, 0.6)

                glBegin(GL_LINE_STRIP)
                # sweep from angle=0 to angle=2π*prog
                for i in range(npts):
                    th = 2.0 * math.pi * (i / float(steps))
                    glVertex2f(sx + rr_arc * math.cos(th), sy + rr_arc * math.sin(th))
                glEnd()

                glLineWidth(1.0)


    _hud_end()


















def _hud_begin():
    glDisable(GL_LIGHTING); glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()

def _hud_end():
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)

def draw_scope_overlay():
    if not SCOPE_VIGNETTE: return
    _hud_begin()
    cx, cy = WIN_W*0.5, WIN_H*0.5
    r = min(WIN_W, WIN_H) * 0.48
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    # draw four corner fans (simple approximation of circular dark edges)
    glColor4f(0.0, 0.0, 0.0, SCOPE_ALPHA)
    seg = 64
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(0,0)
    for i in range(seg+1):
        th = math.pi + i*(math.pi*0.5/seg)
        glVertex2f(cx + r*math.cos(th), cy + r*math.sin(th))
    glEnd()
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(WIN_W,0)
    for i in range(seg+1):
        th = -math.pi*0.5 + i*(math.pi*0.5/seg)
        glVertex2f(cx + r*math.cos(th), cy + r*math.sin(th))
    glEnd()
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(WIN_W,WIN_H)
    for i in range(seg+1):
        th = 0.0 + i*(math.pi*0.5/seg)
        glVertex2f(cx + r*math.cos(th), cy + r*math.sin(th))
    glEnd()
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(0,WIN_H)
    for i in range(seg+1):
        th = math.pi*0.5 + i*(math.pi*0.5/seg)
        glVertex2f(cx + r*math.cos(th), cy + r*math.sin(th))
    glEnd()
    glDisable(GL_BLEND)
    _hud_end()









#center reticle and bullet-direction marker
def draw_center_reticle():
    _hud_begin()
    cx, cy = WIN_W*0.5, WIN_H*0.5

    # target chosen strictly by AIM_CONE_DEG (missile-agnostic)
    e, _ = _screen_center_target(cone_deg=AIM_CONE_DEG)

    # reticle color: green (or keep your gun hit-check if you want)
    glColor3f(1.0, 0.25, 0.25) if crosshair_hits_any_enemy() else glColor3f(0.3, 1.0, 0.3)

    s = RETICLE_SIZE
    glBegin(GL_LINES)
    glVertex2f(cx - s, cy); glVertex2f(cx - 2, cy)
    glVertex2f(cx + 2,  cy); glVertex2f(cx + s,  cy)
    glVertex2f(cx, cy - s);  glVertex2f(cx, cy - 2)
    glVertex2f(cx, cy + 2);  glVertex2f(cx, cy + s)
    glEnd()

    # dotted aim cone ring (fixed size from AIM_CONE_DEG)
    aspect = (WIN_W / float(WIN_H)) if WIN_H else 1.0
    fovy   = FOV_Y_FIRST if cam_mode == 'first' else FOV_Y
    fovx   = 2.0 * math.degrees(math.atan(math.tan(math.radians(fovy)*0.5) * aspect))
    r = (WIN_W * 0.5) * (math.tan(math.radians(AIM_CONE_DEG)) / math.tan(math.radians(fovx*0.5)))
    

    # dotted aim cone ring (no stipple): use points around the circle
    aspect = (WIN_W / float(WIN_H)) if WIN_H else 1.0
    fovy   = FOV_Y_FIRST if cam_mode == 'first' else FOV_Y
    fovx   = 2.0 * math.degrees(math.atan(math.tan(math.radians(fovy)*0.5) * aspect))
    r = (WIN_W * 0.5) * (math.tan(math.radians(AIM_CONE_DEG)) / math.tan(math.radians(fovx*0.5)))

    glColor3f(0.6, 1.0, 0.6)
    seg = 64  # ← this 'seg' (how many sample points around the circle)
    glPointSize(2.5)
    glBegin(GL_POINTS)
    for i in range(seg):
        if (i & 1) == 0:  # every other point → dotted look
            th = (2.0*math.pi*i)/seg
            glVertex2f(cx + r*math.cos(th), cy + r*math.sin(th))
    glEnd()




    glColor3f(0.6, 1.0, 0.6)
    seg = 64
    glBegin(GL_LINE_LOOP)
    for i in range(seg):
        th = (2.0*math.pi*i)/seg
        glVertex2f(cx + r*math.cos(th), cy + r*math.sin(th))
    glEnd()
    glDisable(GL_LINE_STIPPLE)

    _hud_end()



def draw_bullet_direction_marker():
    # project a forward point to screen; shows where bullets go (no gravity drop yet)
    (fx,fy,fz), _, _ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)
    px = pos[0] + fx*VELVEC_LEN
    py = pos[1] + fy*VELVEC_LEN
    pz = pos[2] + fz*VELVEC_LEN
    scr = _project_to_screen(px, py, pz)
    if not scr: return
    _hud_begin()
    sx, sy = scr
    glPointSize(6.0); glColor3f(0.8, 1.0, 0.4)
    glBegin(GL_POINTS); glVertex2f(sx, sy); glEnd()
    _hud_end()










#Compass
def draw_compass():
    _hud_begin()
    cx = WIN_W * 0.5
    y  = WIN_H - 42
    w  = 380.0
    glColor3f(0.15, 0.9, 0.2)
    glBegin(GL_LINES)
    glVertex2f(cx - w*0.5, y); glVertex2f(cx + w*0.5, y)
    glEnd()

    heading = _heading_deg()  # 0..360
    # draw ticks every COMPASS_TICK around center
    degrees_span = 80
    for d in range(-degrees_span, degrees_span+1, COMPASS_TICK):
        hdg = _wrap360(heading + d)
        x = cx + (d / degrees_span) * (w*0.5)
        tick_len = 10 if (abs(d) % 30 == 0) else 6
        glBegin(GL_LINES)
        glVertex2f(x, y - tick_len); glVertex2f(x, y + tick_len)
        glEnd()
        # labels for cardinal directions
        lab = COMPASS_LABELS.get(int(round(hdg)) % 360)
        if lab:
            draw_screen_text(x - 5, y + 12, lab, font=GLUT_BITMAP_HELVETICA_12, color=(0.6,1.0,0.6))
    # center caret
    glBegin(GL_LINES)
    glVertex2f(cx, y + 12); glVertex2f(cx, y + 20)
    glEnd()
    _hud_end()











#subtle target highlight + distance/speed readout
def _screen_center_target(cone_deg=None):
    """Pick enemy closest to screen center within a forward cone (deg).
       LOS-gated so you cannot 'see' through terrain/towers."""
    if not enemies: 
        return None, None
    deg = AIM_CONE_DEG if (cone_deg is None) else cone_deg
    dot_min = math.cos(math.radians(deg))

    (fx,fy,fz), _, _ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)
    best, best_err = None, 1e9
    cx, cy = WIN_W*0.5, WIN_H*0.5
    eye = [pos[0], pos[1], pos[2]]

    for e in enemies:
        vx = e['p'][0]-pos[0]; vy = e['p'][1]-pos[1]; vz = e['p'][2]-pos[2]
        L  = math.sqrt(vx*vx + vy*vy + vz*vz) + 1e-9
        dp = (fx*vx + fy*vy + fz*vz) / L
        if dp < dot_min:
            continue
        # LOS gate
        if not has_line_of_sight(eye, e['p'], clearance=30.0):
            continue
        scr = _project_to_screen(e['p'][0], e['p'][1], e['p'][2])
        if not scr:
            continue
        sx, sy = scr
        err = (sx-cx)*(sx-cx) + (sy-cy)*(sy-cy)
        if err < best_err:
            best, best_err = e, err
    return best, best_err









def gun_can_hit_target(e):
    """True if a straight bullet from the nose would intersect e's hit sphere
       within bullet range (no lead). Slight slop to make confirmable at range."""
    if not e: return False
    (fx,fy,fz), _, _ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)

    NOSE = 90.0
    sx = pos[0] + fx*NOSE
    sy = pos[1] + fy*NOSE
    sz = pos[2] + fz*NOSE

    R  = BULLET_SPEED * BULLET_LIFE  # ~11.4 km with your 3000*3.8
    wx = e['p'][0] - sx; wy = e['p'][1] - sy; wz = e['p'][2] - sz
    t  = wx*fx + wy*fy + wz*fz
    if t < 0.0 or t > R:  # behind or beyond reach
        return False

    px = sx + fx*t; py = sy + fy*t; pz = sz + fz*t
    dx = e['p'][0] - px; dy = e['p'][1] - py; dz = e['p'][2] - pz

    rad = e['hit_r'] * GUN_SUREHIT_SLOP
    return (dx*dx + dy*dy + dz*dz) <= (rad*rad)






def draw_global_pointers():
    if cam_mode != 'third' or not GLOBAL_POINTERS: 
        return
    _hud_begin()
    def draw_pin(world_p, color=(1,0,0), label=""):
        scr = _project_to_screen(world_p[0], world_p[1], world_p[2]+30.0)
        if not scr: return
        sx, sy = scr
        dist = math.hypot(world_p[0]-pos[0], world_p[1]-pos[1])
        s = 12.0 if dist >= VISUAL_RANGE else max(6.0, 12.0 * (dist / float(VISUAL_RANGE)))
        glColor3f(*color)
        glBegin(GL_LINES)
        glVertex2f(sx, sy); glVertex2f(sx, sy+s)
        glVertex2f(sx - s*0.6, sy + s); glVertex2f(sx + s*0.6, sy + s)
        glEnd()
        if label: draw_screen_text(sx + 8, sy + s + 2, label, color=(0,0,0))

    for e in enemies:
        draw_pin(e['p'], color=(1.0,0.2,0.2), label=e.get('name',""))
    for t in towers:
        col = (0.2,0.6,1.0) if t['faction']==FACTION_FRIEND else (1.0,0.2,0.2)
        draw_pin([t['p'][0],t['p'][1],GROUND_PLANE_Z], color=col, label="Tower")
    for u in aa_units:
        draw_pin([u['p'][0],u['p'][1],u['z']], color=(1.0,0.55,0.15), label="AA")
    for u in sam_units:
        draw_pin([u['p'][0],u['p'][1],u['z']], color=(0.7,0.2,1.0), label="SAM")
    for b in bunkers:
        draw_pin([b['p'][0],b['p'][1],b['z']], color=(0.1,0.1,0.1), label="Bunker")
    _hud_end()




















def draw_hud():
    # HUD text + radar in one ortho pass
    glDisable(GL_LIGHTING); glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW);  glPushMatrix(); glLoadIdentity()

    # top-left status strip
    glColor3f(1,1,1)
    camtxt = 'FP' if cam_mode=='first' else ('TP-LOCK' if cam_lock_follow else 'TP-Free')
    s = f"Score {score}   Speed {int(speed)}   Alt {int(pos[2])}   Cam {camtxt}   Y:{int(yaw_deg)} P:{int(pitch_deg)} R:{int(roll_deg)}"
    glRasterPos2f(10, WIN_H-24)
    for ch in s: glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # IMPORTANT: draw radar while still in HUD ortho
    draw_radar()

    draw_player_health()

    draw_legend_overlay()


    # close HUD ortho
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)

    # First-person extras manage their own ortho pushes
    if cam_mode == 'first':
        draw_scope_overlay()
        draw_compass()
        draw_center_reticle()
        draw_bullet_direction_marker()
        draw_target_highlight_and_stats()
        draw_lock_hud()
        draw_weapon_status()


    draw_global_pointers() # always on top of 3rd-person view






def setup_camera():
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    fov = FOV_Y_FIRST if cam_mode == 'first' else FOV_Y_THIRD
    gluPerspective(fov, WIN_W/float(max(1, WIN_H)), NEAR_Z, FAR_Z)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()
    (fx,fy,fz), _, _ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)

    if cam_mode == 'first':
        # small offset forward + slight up for better sightline
        eye = [pos[0] + fx*10.0, pos[1] + fy*10.0, pos[2] + fz*10.0 + 2.0]
        ctr = [eye[0] + fx*120.0, eye[1] + fy*120.0, eye[2] + fz*120.0]
        gluLookAt(eye[0],eye[1],eye[2], ctr[0],ctr[1],ctr[2], 0,0,1)
    else:
        if cam_lock_follow:
            cx = pos[0] - fx*cam_dist; cy = pos[1] - fy*cam_dist; cz = pos[2] - fz*cam_dist + cam_height
            ctr = [pos[0] + fx*100.0, pos[1] + fy*100.0, pos[2] + fz*100.0]
            gluLookAt(cx,cy,cz, ctr[0],ctr[1],ctr[2], 0,0,1)
        else:
            oy,op = deg2rad(orbit_yaw), deg2rad(orbit_pitch)
            ox = math.cos(oy)*math.cos(op); oyv = math.sin(oy)*math.cos(op); oz = math.sin(op)
            cx = pos[0] - ox*cam_dist; cy = pos[1] - oyv*cam_dist; cz = pos[2] + oz*cam_dist + cam_height
            ctr = [pos[0] + fx*100.0, pos[1] + fy*100.0, pos[2] + fz*100.0]
            gluLookAt(cx,cy,cz, ctr[0],ctr[1],ctr[2], 0,0,1)





def steer_toward_center(p, yaw_deg, margin=1200.0):
    """Clamp to PLAY_EXTENT and bias yaw toward center if we touch the rim."""
    half = PLAY_EXTENT
    cx = cy = 0.0
    x, y = p[0], p[1]
    bumped = False
    if x >  half - margin: x =  half - margin; bumped = True
    if x < -half + margin: x = -half + margin; bumped = True
    if y >  half - margin: y =  half - margin; bumped = True
    if y < -half + margin: y = -half + margin; bumped = True
    if bumped:
        yaw_rad = math.atan2(cy - y, cx - x)
        yaw_deg = rad2deg(yaw_rad)
    return (x, y, yaw_deg)

def _steer_towards(e, target_xy, rate_deg_per_s, dt):
    # steer enemy yaw toward target point in XY
    tx, ty = target_xy
    desired = rad2deg(math.atan2(ty - e['p'][1], tx - e['p'][0]))
    # smallest angle difference
    diff = (desired - e['yaw'] + 540.0) % 360.0 - 180.0
    max_turn = rate_deg_per_s * dt
    diff = clamp(diff, -max_turn, +max_turn)
    e['yaw'] += diff

def _project_to_screen(x, y, z):
    mv  = glGetDoublev(GL_MODELVIEW_MATRIX)
    pj  = glGetDoublev(GL_PROJECTION_MATRIX)
    vp  = glGetIntegerv(GL_VIEWPORT)
    wx, wy, wz = gluProject(x, y, z, mv, pj, vp)
    if wz < 0.0 or wz > 1.0: return None
    return wx, wy

def draw_screen_text(x, y, text, font=GLUT_BITMAP_HELVETICA_12, color=(0.95, 0.95, 1.0)):
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW);  glPushMatrix(); glLoadIdentity()
    glColor3f(*color)
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)

def _draw_name_label(e):
    # draw simple 3D world-space label just above the plane
    glDisable(GL_LIGHTING)
    glColor3f(0.0, 0.0, 0.0)
    glRasterPos3f(e['p'][0], e['p'][1], e['p'][2] + e['hit_r'] + 20.0)
    text = e['name']
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

# ---------------- GLUT ----------------
def display():
    global last_time
    now = time.time()
    if last_time is None: last_time = now
    dt = min(now - last_time, 1.0/60.0); last_time = now

    update(dt)

    glViewport(0, 0, WIN_W, WIN_H)
    glClearColor(0.53, 0.81, 0.92, 1.0)  # sky blue
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)

    setup_camera()

    draw_ground(pos[0], pos[1])

    draw_world()  # buildings, towers, ground units

    # Control-surface animation driven by attitude (visual)
    el_pitch = clamp(pitch_deg * 0.25, -ELV_MAX, ELV_MAX)
    el_roll  = clamp(roll_deg  * 0.70, -ELV_MAX, ELV_MAX)
    elevonL  = clamp(el_pitch + el_roll, -ELV_MAX, ELV_MAX)
    elevonR  = clamp(el_pitch - el_roll, -ELV_MAX, ELV_MAX)

    if cam_mode != 'first':
      draw_f117(elevonL, elevonR, rudder_deg_vis=rudder_deg)

    draw_enemies()
    draw_bullets()
    draw_flares()
    draw_missiles()      # draw missiles in 3D before HUD
    draw_aa_shots()

    draw_explosions()

    draw_dev_hitboxes()


    draw_hud()

    glutSwapBuffers()
    glutPostRedisplay()

def reshape(w, h):
    global WIN_W, WIN_H
    WIN_W, WIN_H = max(1,w), max(1,h)

def keyboard_down(key, x, y):
    global cam_mode, cam_lock_follow, orbit_yaw, orbit_pitch, dev_colors
    global lock_active, locked_key, lock_candidate

    if isinstance(key, bytes) and len(key)==1 and 65 <= key[0] <= 90: k = bytes([key[0]+32])
    else: k = key
    if k == b'\x1b': sys.exit(0)
    keys_down.add(k)

    if k == b'h':
        globals()['SHOW_HITBOXES'] = not globals().get('SHOW_HITBOXES', False)
        return


    if k == b'\\': dev_colors = not dev_colors
    if k == b'l':  # god mode (invincible)
        globals()['PLAYER_INVINCIBLE'] = not globals().get('PLAYER_INVINCIBLE', False)
        return

    if k == b' ': spawn_bullet()
    if k == b't':
        cam_mode = 'first' if cam_mode=='third' else 'third'
        cam_lock_follow = False
    if k == b'\t':
        cycle_target(+1)

    if k in (b'c',) and cam_mode=='third':
        cam_lock_follow = True
        (fx,fy,fz), _, _ = rotation_matrix(yaw_deg, pitch_deg, roll_deg)
        orbit_yaw   = rad2deg(math.atan2(fy, fx))
        orbit_pitch = rad2deg(math.asin(clamp(fz, -1.0, 1.0)))

    if k == b'p':  # pointers cheat (TPV only)
        global GLOBAL_POINTERS
        GLOBAL_POINTERS = not GLOBAL_POINTERS
        return


    if k == b';':  # legend slide panel
        global SHOW_LEGEND, legend_anim
        SHOW_LEGEND = not SHOW_LEGEND
        legend_anim['target'] = 16.0 if SHOW_LEGEND else -320.0
        return




    
    # Missile select: 1/2/3
    if k in (b'1', b'2', b'3'):
        sel = {'1':'A2A_S','2':'A2A_M','3':'A2S_G'}[k.decode()]
        if sel != MSL_SELECTED:
            # switch missile: reset lock so UI is consistent
            globals()['MSL_SELECTED'] = sel
            globals()['_target_id'] = None
            globals()['_lock_timer'] = 0.0
            globals()['_lock_state'] = 'NONE'
        return

    # Arm missile on press (fire on release)
    if k == MSL_FIRE_KEY:
        globals()['msl_armed'] = True
        return

    # Drop flare on Z (cooldown)
    if k in (b'z',):
        now = time.time()
        if now - last_flare_time >= FLARE_COOLDOWN:
            drop_flare()
            globals()['last_flare_time'] = now
        return






    try: mods = glutGetModifiers()
    except Exception: mods = 0
    if k in MKEYS and (mods & GLUT_ACTIVE_SHIFT): lock_candidate = k
    if k in MKEYS: lock_active = False; locked_key = None

def keyboard_up(key, x, y):
    global lock_active, locked_key, lock_candidate
    if isinstance(key, bytes) and len(key)==1 and 65 <= key[0] <= 90: k = bytes([key[0]+32])
    else: k = key
    if k in keys_down: keys_down.remove(k)
    if k == lock_candidate and k in MKEYS:
        lock_active, locked_key, lock_candidate = True, k, None
    elif k in MKEYS and lock_candidate == k:
        lock_candidate = None
    
    if k == MSL_FIRE_KEY and globals().get('msl_armed'):
        release_missile_trigger()


def special_keys(key, x, y):
    global orbit_yaw, orbit_pitch, cam_lock_follow
    if cam_mode == 'third':
        if key in (GLUT_KEY_LEFT, GLUT_KEY_RIGHT, GLUT_KEY_UP, GLUT_KEY_DOWN):
            cam_lock_follow = False
        if key == GLUT_KEY_LEFT:  orbit_yaw   += 2.0
        if key == GLUT_KEY_RIGHT: orbit_yaw   -= 2.0
        if key == GLUT_KEY_UP:    orbit_pitch = clamp(orbit_pitch + 2.0, -80.0, 80.0)
        if key == GLUT_KEY_DOWN:  orbit_pitch = clamp(orbit_pitch - 2.0, -80.0, 80.0)


            

def mouse(button, state, x, y):
    # Right mouse behaves like X
    if button == GLUT_RIGHT_BUTTON:
        if state == GLUT_DOWN:
            globals()['msl_armed'] = True
        elif state == GLUT_UP:
            release_missile_trigger()


def init_gl():
    glPointSize(6.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE); glCullFace(GL_BACK)
    glDisable(GL_LIGHTING)

def main():
    try: glutInit(sys.argv)
    except TypeError: glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutCreateWindow(b"Operation Nighthawk")
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard_down)
    glutKeyboardUpFunc(keyboard_up)
    glutSpecialFunc(special_keys)
    glutMouseFunc(mouse)
    init_gl()

    world_init()
    spawn_bunker_cluster()

    glutMainLoop()

if __name__ == "__main__":
    main()