import pygame
import math
import random
import json
import os
import array

# Configurazione del Mixer Audio
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

# Costanti dello schermo e del gioco
WIDTH, HEIGHT = 800, 600
FPS = 60

# Colori
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CYAN = (112, 164, 178)
GREEN = (88, 141, 67)
RED = (136, 57, 50)
YELLOW = (184, 199, 111)
BLUE = (50, 100, 255)

# Tour del Sistema Solare (Ordinati per gravità crescente)
# La potenza normale è 0.06, il Super Boost è 0.12.
PLANETS = [
    {"name": "DEIMOS",   "gravity": 0.008, "color": (150, 150, 150)}, # Luna di Marte, leggerissima
    {"name": "PLUTONE",  "gravity": 0.010, "color": (130, 200, 220)}, # Il nostro nano preferito
    {"name": "EUROPA",   "gravity": 0.013, "color": (200, 230, 255)}, # Luna di Giove (Ghiacciata)
    {"name": "LUNA",     "gravity": 0.015, "color": WHITE},           # La nostra Luna
    {"name": "TITANO",   "gravity": 0.016, "color": (210, 180, 100)}, # Luna di Saturno
    {"name": "IO",       "gravity": 0.018, "color": (255, 200, 50)},  # Luna vulcanica di Giove
    {"name": "MERCURIO", "gravity": 0.022, "color": (170, 160, 150)}, 
    {"name": "MARTE",    "gravity": 0.023, "color": (200, 80, 50)},
    {"name": "URANO",    "gravity": 0.028, "color": (150, 220, 255)},
    {"name": "VENERE",   "gravity": 0.030, "color": (230, 200, 150)},
    {"name": "TERRA",    "gravity": 0.032, "color": (100, 160, 255)},
    {"name": "SATURNO",  "gravity": 0.035, "color": (240, 220, 160)},
    {"name": "NETTUNO",  "gravity": 0.040, "color": (50, 100, 200)},
    {"name": "GIOVE",    "gravity": 0.080, "color": (200, 160, 120)}  # Gravità estrema! Obbligatorio il Super Boost!
]

# Nuovi parametri di spinta
NORMAL_THRUST_POWER = 0.06
SUPER_THRUST_POWER = 0.12
NORMAL_FUEL_COST = 1.5
SUPER_FUEL_COST = 4.5

ROTATION_SPEED = 3.0

# ==========================================
# GESTIONE CONFIGURAZIONE E SALVATAGGIO
# ==========================================
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "enable_extra_lives": True,
    "extra_life_threshold": 10000
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
    else:
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return DEFAULT_CONFIG

# ==========================================
# GENERATORE DI SUONI 8-BIT
# ==========================================
def generate_8bit_sounds():
    sounds = {}
    sample_rate = 44100

    # Suono Razzo (Rumore Bianco)
    thrust_len = int(sample_rate * 0.1)
    thrust_buf = array.array('h', [int(random.uniform(-4000, 4000)) for _ in range(thrust_len)])
    sounds['thrust'] = pygame.mixer.Sound(buffer=thrust_buf.tobytes())
    
    # Suono Super Boost (Più forte e distorto)
    super_buf = array.array('h', [int(random.uniform(-8000, 8000)) for _ in range(thrust_len)])
    sounds['super_thrust'] = pygame.mixer.Sound(buffer=super_buf.tobytes())

    # Suono Allarme
    alarm_len = int(sample_rate * 0.5)
    alarm_buf = array.array('h')
    for i in range(alarm_len):
        freq = 800 if i < alarm_len // 2 else 600
        phase = (i * freq) / sample_rate
        val = 6000 if (phase % 1.0) < 0.5 else -6000
        alarm_buf.append(val)
    sounds['alarm'] = pygame.mixer.Sound(buffer=alarm_buf.tobytes())
    sounds['alarm'].set_volume(0.3)

    # Suono Crash
    crash_len = int(sample_rate * 1.5)
    crash_buf = array.array('h')
    for i in range(crash_len):
        decay = max(0, 1.0 - (i / crash_len))
        val = int(random.uniform(-18000, 18000) * (decay**2))
        crash_buf.append(val)
    sounds['crash'] = pygame.mixer.Sound(buffer=crash_buf.tobytes())
    sounds['crash'].set_volume(0.7)

    return sounds

# ==========================================
# MOTORE PARTICELLE
# ==========================================
class Particle:
    def __init__(self, x, y, vx, vy, color, lifespan):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifespan = lifespan
        self.max_life = lifespan

    def update(self, gravity):
        self.x += self.vx
        self.vy += gravity * 0.5
        self.y += self.vy
        self.lifespan -= 1

    def draw(self, surface):
        if self.lifespan > 0:
            ratio = self.lifespan / self.max_life
            r = int(self.color[0] * ratio)
            g = int(self.color[1] * ratio)
            b = int(self.color[2] * ratio)
            r, g, b = max(0, r), max(0, g), max(0, b)
            
            size = max(1, int(4 * ratio))
            pygame.draw.rect(surface, (r, g, b), (int(self.x), int(self.y), size, size))

def spawn_thrust(lander, particles):
    rad = math.radians(lander.angle)
    sin_a = math.sin(rad)
    cos_a = math.cos(rad)
    
    nozzle_x = lander.x - 12 * sin_a
    nozzle_y = lander.y + 12 * cos_a
    
    # Se sta usando il Super Boost, facciamo più particelle, più veloci, di colore azzurro
    if lander.is_super_thrusting:
        particle_count = 8
        speed_mult = 2.0
        colors = [CYAN, BLUE, WHITE]
    else:
        particle_count = 4
        speed_mult = 1.0
        colors = [YELLOW, RED, WHITE]

    for _ in range(particle_count):
        p_vx = -sin_a * random.uniform(2 * speed_mult, 5 * speed_mult) + random.uniform(-1, 1)
        p_vy = cos_a * random.uniform(2 * speed_mult, 5 * speed_mult) + random.uniform(-1, 1)
        color = random.choice(colors)
        particles.append(Particle(nozzle_x, nozzle_y, p_vx, p_vy, color, random.randint(15, 30)))

def spawn_explosion(x, y, particles):
    for _ in range(120):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1, 8)
        p_vx = math.cos(angle) * speed
        p_vy = math.sin(angle) * speed
        color = random.choice([CYAN, CYAN, WHITE, YELLOW, RED])
        particles.append(Particle(x, y, p_vx, p_vy, color, random.randint(30, 90)))

# ==========================================
# CLASSI DEL GIOCO
# ==========================================
class Lander:
    def __init__(self, config):
        self.config = config
        self.lives = 3
        self.score = 0
        self.next_life_at = self.config["extra_life_threshold"]
        self.reset_position()
        
    def reset_position(self):
        self.x = WIDTH // 2
        self.y = 50
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.fuel = 1000.0
        self.is_thrusting = False
        self.is_super_thrusting = False
        self.crashed = False
        self.landed = False

    def update(self, keys, current_gravity):
        if self.crashed or self.landed:
            return

        if keys[pygame.K_LEFT]: self.angle -= ROTATION_SPEED
        if keys[pygame.K_RIGHT]: self.angle += ROTATION_SPEED

        # Sistema di Propulsione (Normale o Super Boost)
        if keys[pygame.K_SPACE] and self.fuel > 0:
            if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
                self.is_super_thrusting = True
                self.is_thrusting = False
                thrust = SUPER_THRUST_POWER
                cost = SUPER_FUEL_COST
            else:
                self.is_thrusting = True
                self.is_super_thrusting = False
                thrust = NORMAL_THRUST_POWER
                cost = NORMAL_FUEL_COST
                
            self.fuel -= cost
            rad = math.radians(self.angle)
            self.vx += math.sin(rad) * thrust
            self.vy -= math.cos(rad) * thrust
        else:
            self.is_thrusting = False
            self.is_super_thrusting = False

        self.vy += current_gravity
        self.x += self.vx
        self.y += self.vy

    def draw(self, surface):
        rad = math.radians(self.angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        def transform(points):
            rotated = []
            for px, py in points:
                rx = px * cos_a - py * sin_a
                ry = px * sin_a + py * cos_a
                rotated.append((self.x + rx, self.y + ry))
            return rotated

        body = [(-8, -6), (8, -6), (12, 2), (8, 8), (-8, 8), (-12, 2)]
        pygame.draw.polygon(surface, CYAN, transform(body), 2)
        pygame.draw.lines(surface, CYAN, False, transform([(-10, 6), (-16, 14)]), 2)
        pygame.draw.lines(surface, CYAN, False, transform([(10, 6), (16, 14)]), 2)
        pygame.draw.lines(surface, CYAN, False, transform([(-20, 14), (-12, 14)]), 2)
        pygame.draw.lines(surface, CYAN, False, transform([(12, 14), (20, 14)]), 2)
        pygame.draw.polygon(surface, CYAN, transform([(-4, 8), (-6, 12), (6, 12), (4, 8)]), 1)

class Terrain:
    def __init__(self, level):
        self.points = []
        self.pads = []
        self.generate(level)

    def displace(self, p1, p2, roughness, iterations):
        points = [p1, p2]
        for _ in range(iterations):
            new_points = []
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i+1]
                mid_x = (x1 + x2) / 2
                disp = random.uniform(-roughness, roughness) * (x2 - x1)
                mid_y = max(150, min(HEIGHT - 20, (y1 + y2) / 2 + disp))
                new_points.extend([(x1, y1), (mid_x, mid_y)])
            new_points.append(points[-1])
            points = new_points
        return points

    def generate(self, level):
        self.points = []
        self.pads = []
        
        pad_configs = [
            {"width": 100, "mult": 1, "color": GREEN},
            {"width": 65,  "mult": 3, "color": YELLOW},
            {"width": 40,  "mult": 5, "color": RED}
        ]
        random.shuffle(pad_configs)
        zones = [(30, 230), (250, 350), (460, 750)]
        
        for i in range(3):
            cfg = pad_configs[i]
            w = cfg["width"]
            x = random.randint(zones[i][0], zones[i][1] - w)
            y = random.randint(300, HEIGHT - 80)
            self.pads.append({"x1": x, "x2": x + w, "y": y, "mult": cfg["mult"], "color": cfg["color"]})
            
        key_points = [(0, random.randint(250, 450))]
        for p in self.pads:
            key_points.append((p["x1"], p["y"]))
            key_points.append((p["x2"], p["y"]))
        key_points.append((WIDTH, random.randint(250, 450)))
        
        final_points = []
        for i in range(len(key_points) - 1):
            p1 = key_points[i]
            p2 = key_points[i+1]
            if any(p1[0] == p["x1"] and p2[0] == p["x2"] for p in self.pads):
                final_points.append(p1)
            else:
                final_points.extend(self.displace(p1, p2, 0.5, 4)[:-1])
        final_points.append(key_points[-1])
        self.points = final_points

    def draw(self, surface):
        if len(self.points) > 1:
            pygame.draw.lines(surface, WHITE, False, self.points, 2)
        for pad in self.pads:
            pygame.draw.line(surface, pad["color"], (pad["x1"], pad["y"]), (pad["x2"], pad["y"]), 4)

def check_landing(lander, terrain):
    if lander.x < 0 or lander.x > WIDTH or lander.y > HEIGHT:
        return "crash", 0

    for i in range(len(terrain.points) - 1):
        x1, y1 = terrain.points[i]
        x2, y2 = terrain.points[i+1]
        
        if x1 <= lander.x <= x2:
            t = (lander.x - x1) / (x2 - x1) if x2 != x1 else 0
            ground_y = y1 + t * (y2 - y1)
            
            if lander.y + 14 >= ground_y:
                is_pad = False
                multiplier = 0
                for pad in terrain.pads:
                    if pad["x1"] <= lander.x - 15 and lander.x + 15 <= pad["x2"] and y1 == y2:
                        is_pad = True
                        multiplier = pad["mult"]
                        break
                
                speed = math.hypot(lander.vx, lander.vy)
                if is_pad and speed < 1.5 and abs(lander.angle) < 12:
                    return "land", multiplier
                else:
                    return "crash", 0
    return "flying", 0

def draw_hud(surface, font, lander, level, planet):
    score_txt = font.render(f"SCORE: {lander.score}", True, WHITE)
    lives_txt = font.render(f"LIVES: {lander.lives}", True, WHITE)
    level_txt = font.render(f"LEVEL: {level}", True, WHITE)
    
    planet_txt = font.render(f"DESTINAZIONE: {planet['name']} (G: {planet['gravity']:.3f})", True, planet['color'])
    surface.blit(planet_txt, (WIDTH // 2 - planet_txt.get_width() // 2, 10))

    surface.blit(score_txt, (10, 10))
    surface.blit(lives_txt, (10, 40))
    surface.blit(level_txt, (WIDTH - 150, 10))
    
    fuel_pct = max(0, lander.fuel / 1000.0)
    pygame.draw.rect(surface, WHITE, (WIDTH // 2 - 100, 35, 200, 10), 2)
    is_low_fuel = fuel_pct <= 0.3
    pygame.draw.rect(surface, RED if is_low_fuel else GREEN, (WIDTH // 2 - 98, 37, 196 * fuel_pct, 6))
    
    fuel_txt = font.render("FUEL", True, WHITE)
    surface.blit(fuel_txt, (WIDTH // 2 - 25, 48))

    # Indicatore Super Boost
    if lander.is_super_thrusting:
        boost_txt = font.render("SUPER BOOST!", True, CYAN)
        surface.blit(boost_txt, (WIDTH // 2 - boost_txt.get_width() // 2, 70))

def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Commodore 64 Lunar Lander")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Courier", 20, bold=True)
    big_font = pygame.font.SysFont("Courier", 40, bold=True)

    config = load_config()
    sounds = generate_8bit_sounds()
    
    ch_thrust = pygame.mixer.Channel(0)
    ch_alarm = pygame.mixer.Channel(1)
    ch_crash = pygame.mixer.Channel(2)

    lander = Lander(config)
    level = 1
    terrain = Terrain(level)
    particles = []
    
    state = "START_SCREEN"
    timer = 0

    running = True
    while running:
        clock.tick(FPS)
        keys = pygame.key.get_pressed()
        
        current_planet = PLANETS[(level - 1) % len(PLANETS)]
        current_gravity = current_planet["gravity"]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if state == "START_SCREEN" and event.type == pygame.KEYDOWN:
                state = "PLAYING"

        for p in particles[:]:
            p.update(current_gravity)
            if p.lifespan <= 0:
                particles.remove(p)

        if state == "PLAYING":
            lander.update(keys, current_gravity)
            
            if lander.is_thrusting or lander.is_super_thrusting:
                spawn_thrust(lander, particles)
                if not ch_thrust.get_busy():
                    # Suono diverso se è Super Boost
                    sound_to_play = sounds['super_thrust'] if lander.is_super_thrusting else sounds['thrust']
                    ch_thrust.play(sound_to_play, loops=-1)
            else:
                ch_thrust.stop()

            fuel_pct = lander.fuel / 1000.0
            if 0 < fuel_pct <= 0.3:
                if not ch_alarm.get_busy():
                    ch_alarm.play(sounds['alarm'], loops=-1)
            else:
                ch_alarm.stop()

            status, mult = check_landing(lander, terrain)
            
            if status == "crash":
                lander.crashed = True
                lander.lives -= 1
                state = "CRASHED"
                timer = pygame.time.get_ticks()
                
                ch_thrust.stop()
                ch_alarm.stop()
                ch_crash.play(sounds['crash'])
                
                spawn_explosion(lander.x, lander.y, particles)
                
            elif status == "land":
                lander.landed = True
                points_earned = 500 * mult
                lander.score += points_earned
                
                if config["enable_extra_lives"]:
                    if lander.score >= lander.next_life_at:
                        lander.lives += 1
                        lander.next_life_at += config["extra_life_threshold"]
                        
                state = "LANDED"
                timer = pygame.time.get_ticks()
                ch_thrust.stop()
                ch_alarm.stop()

        elif state == "CRASHED":
            if pygame.time.get_ticks() - timer > 2000:
                if lander.lives > 0:
                    lander.reset_position()
                    particles.clear()
                    state = "PLAYING"
                else:
                    state = "GAMEOVER"

        elif state == "LANDED":
            if pygame.time.get_ticks() - timer > 2000:
                level += 1
                terrain.generate(level)
                lander.reset_position()
                particles.clear()
                state = "PLAYING"

        screen.fill(BLACK)
        terrain.draw(screen)
        
        for p in particles:
            p.draw(screen)
        
        if not lander.crashed:
            lander.draw(screen)
            
        if state == "START_SCREEN":
            title_msg = big_font.render("LUNAR LANDER", True, CYAN)
            screen.blit(title_msg, (WIDTH//2 - title_msg.get_width()//2, HEIGHT//2 - 50))
            if pygame.time.get_ticks() // 500 % 2 == 0:
                start_msg = font.render("Premi un tasto per iniziare", True, WHITE)
                screen.blit(start_msg, (WIDTH//2 - start_msg.get_width()//2, HEIGHT//2 + 10))
            
            controls_msg = font.render("Frecce: Ruota | SPAZIO: Razzo | SPAZIO+CTRL: SUPER BOOST", True, YELLOW)
            screen.blit(controls_msg, (WIDTH//2 - controls_msg.get_width()//2, HEIGHT - 50))
        else:
            draw_hud(screen, font, lander, level, current_planet)

            if state == "CRASHED" and lander.lives > 0:
                msg = big_font.render("CRASHED!", True, RED)
                screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2))
            elif state == "LANDED":
                msg = big_font.render("GOOD LANDING!", True, GREEN)
                screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2))
            elif state == "GAMEOVER":
                msg = big_font.render("GAME OVER", True, RED)
                screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 20))
                sub_msg = font.render("Premi INVIO per ricominciare", True, WHITE)
                screen.blit(sub_msg, (WIDTH//2 - sub_msg.get_width()//2, HEIGHT//2 + 30))
                
                if keys[pygame.K_RETURN]:
                    lander = Lander(config)
                    level = 1
                    terrain.generate(level)
                    particles.clear()
                    state = "PLAYING"

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
