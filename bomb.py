import pygame
import random
import sys
import json
from pathlib import Path
from dataclasses import dataclass, asdict

pygame.init()
BASE_WIDTH, BASE_HEIGHT = 540, 720
FPS = 60

BG_TOP    = (235, 240, 255)
BG_BOTTOM = (250, 250, 250)
PANEL     = (255, 255, 255)
TEXT      = (20, 22, 25)
MUTED     = (130, 135, 145)
PRIMARY   = (52, 105, 255)
PRIMARY_D = (42, 90, 230)
OK        = (32, 185, 100)
WARN      = (255, 170, 30)
DANGER    = (230, 60, 60)
OUTLINE   = (220, 224, 233)
GOLD      = (240, 200, 20)

RED   = (220, 40, 40)
BLUE  = (40, 90, 235)
GREEN = (34, 170, 85)
ORANGE= (255, 140, 0)
PURPLE= (145, 70, 255)

SAVE_FILE = Path("save.json")

@dataclass
class SaveData:
    best: float = 0.0
    volume: int = 70
    difficulty: str = "Normal"   
    fullscreen: bool = False
    coins_total: int = 0
    upgrades: dict = None        

def load_save():
    if SAVE_FILE.exists():
        try:
            raw = json.loads(SAVE_FILE.read_text())
            upg = raw.get("upgrades") or {"shield":0,"magnet":0,"drops":0,"second":0}
            return SaveData(
                best=float(raw.get("best", 0.0)),
                volume=int(raw.get("volume", 70)),
                difficulty=str(raw.get("difficulty", "Normal")),
                fullscreen=bool(raw.get("fullscreen", False)),
                coins_total=int(raw.get("coins_total", 0)),
                upgrades=upg
            )
        except Exception:
            pass
    return SaveData(upgrades={"shield":0,"magnet":0,"drops":0,"second":0})

def save_save(s: SaveData):
    try:
        SAVE_FILE.write_text(json.dumps(asdict(s), ensure_ascii=False, indent=2))
    except Exception:
        pass

save = load_save()

flags = pygame.FULLSCREEN if save.fullscreen else 0
screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT), flags)
pygame.display.set_caption("DODGE! — Shop & UI Edition")
clock = pygame.time.Clock()
font  = pygame.font.SysFont(None, 26)
font_mid = pygame.font.SysFont(None, 32)
font_big = pygame.font.SysFont(None, 48)

pygame.mixer.music.set_volume(save.volume/100.0)

def draw_gradient_bg(surf):
    w, h = surf.get_size()
    for y in range(h):
        t = y / max(1, h-1)
        r = int(BG_TOP[0]*(1-t) + BG_BOTTOM[0]*t)
        g = int(BG_TOP[1]*(1-t) + BG_BOTTOM[1]*t)
        b = int(BG_TOP[2]*(1-t) + BG_BOTTOM[2]*t)
        pygame.draw.line(surf, (r,g,b), (0,y), (w,y))

def text(s, x, y, c=TEXT, center=False, big=False, mid=False):
    f = font_big if big else font_mid if mid else font
    img = f.render(s, True, c)
    r = img.get_rect()
    if center:
        r.center = (x, y)
    else:
        r.topleft = (x, y)
    screen.blit(img, r)

def rounded_panel(rect, fill=PANEL, border=OUTLINE, radius=18, shadow=True):
    if shadow:
        sh = pygame.Surface((rect.w+12, rect.h+12), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0,0,0,40), sh.get_rect(), border_radius=radius+6)
        screen.blit(sh, (rect.x-6, rect.y+6))
    pygame.draw.rect(screen, fill, rect, border_radius=radius)
    pygame.draw.rect(screen, border, rect, width=1, border_radius=radius)

class Button:
    def __init__(self, rect, label, kind="primary"):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.kind = kind

    def draw(self, mouse):
        hover = self.rect.collidepoint(mouse)
        if self.kind == "primary":
            color = PRIMARY_D if hover else PRIMARY
            pygame.draw.rect(screen, color, self.rect, border_radius=12)
            text(self.label, self.rect.centerx, self.rect.centery, (255,255,255), center=True)
        elif self.kind == "ghost":
            pygame.draw.rect(screen, OUTLINE, self.rect, width=1, border_radius=12)
            text(self.label, self.rect.centerx, self.rect.centery, PRIMARY if hover else TEXT, center=True)
        elif self.kind == "danger":
            color = (210,50,50) if not hover else (180,40,40)
            pygame.draw.rect(screen, color, self.rect, border_radius=12)
            text(self.label, self.rect.centerx, self.rect.centery, (255,255,255), center=True)

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

class Slider:
    def __init__(self, rect, value=0.7):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.drag = False

    def draw(self, mouse):
        x,y,w,h = self.rect
        pygame.draw.rect(screen, OUTLINE, (x, y+h//2-3, w, 6), border_radius=6)
        pygame.draw.rect(screen, PRIMARY, (x, y+h//2-3, int(w*self.value), 6), border_radius=6)
        knob_x = x + int(w*self.value)
        pygame.draw.circle(screen, PRIMARY, (knob_x, y+h//2), 10)
        pygame.draw.circle(screen, (255,255,255), (knob_x, y+h//2), 8)

    def handle(self, event):
        x,y,w,h = self.rect
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if pygame.Rect(x, y, w, h).collidepoint(event.pos):
                self.drag = True
                self.value = max(0, min(1, (event.pos[0]-x)/w))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.drag = False
        elif event.type == pygame.MOUSEMOTION and self.drag:
            self.value = max(0, min(1, (event.pos[0]-x)/w))

class Select:
    def __init__(self, rect, options, selected=0):
        self.rect = pygame.Rect(rect)
        self.options = options
        self.selected = selected

    def draw(self, mouse):
        pygame.draw.rect(screen, OUTLINE, self.rect, width=1, border_radius=10)
        s = self.options[self.selected]
        text(s, self.rect.centerx, self.rect.centery, PRIMARY, center=True)

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.selected = (self.selected + 1) % len(self.options)

def toggle_fullscreen():
    save.fullscreen = not save.fullscreen
    save_save(save)
    flags = pygame.FULLSCREEN if save.fullscreen else 0
    return pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT), flags)

DIFF_PROFILES = {
    "Easy":   dict(BOMB_SPEED0=160.0, SPAWN_MS0=900, SPAWN_MIN_MS=320, STEP_V=24.0, STEP_SPAWN=60),
    "Normal": dict(BOMB_SPEED0=185.0, SPAWN_MS0=780, SPAWN_MIN_MS=260, STEP_V=28.0, STEP_SPAWN=70),
    "Hard":   dict(BOMB_SPEED0=210.0, SPAWN_MS0=700, SPAWN_MIN_MS=220, STEP_V=34.0, STEP_SPAWN=80),
}

PLAYER_SIZE   = 52
PLAYER_SPEED  = 340.0
BOMB_SIZE     = 30
DIFF_EVERY_S  = 10

POWERUP_MS    = (5600, 8200)   
SLOW_FACTOR   = 0.5
SLOW_TIME     = 5.0
SHIELD_TIME   = 8.0           
MAGNET_TIME   = 7.0           
BOMB_CLEAN_LABEL = "Ω"

COIN_MS       = 900
COIN_VY       = 150.0
COIN_MAGNET_ACCEL = 520.0
COIN_MAX_SPEED    = 440.0

NEW_BOMB  = pygame.USEREVENT + 1
NEW_PWR   = pygame.USEREVENT + 2
NEW_COIN  = pygame.USEREVENT + 3

class Particle:
    __slots__ = ("x","y","vx","vy","life","color","size")
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.vx = random.uniform(-120, 120)
        self.vy = random.uniform(-60, -220)
        self.life = random.uniform(0.5, 0.9)
        self.color = color
        self.size = random.randint(2,4)

    def update(self, dt):
        self.life -= dt
        self.vy += 380 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, surf):
        if self.life > 0:
            alpha = max(0, min(255, int(255 * (self.life / 0.9))))
            s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            s.fill((*self.color, alpha))
            surf.blit(s, (int(self.x), int(self.y)))

class Player:
    def __init__(self):
        w, h = screen.get_size()
        self.rect = pygame.Rect(w//2 - PLAYER_SIZE//2, h-PLAYER_SIZE-16, PLAYER_SIZE, PLAYER_SIZE)
        self.speed = PLAYER_SPEED
        self.has_shield = False
        self.shield_time_left = 0.0
        self.magnet_time_left = 0.0
        self.second_chance_available = bool(save.upgrades.get("second",0))

    def update(self, dt):
        w, h = screen.get_size()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  self.rect.x -= int(self.speed * dt)
        if keys[pygame.K_RIGHT]: self.rect.x += int(self.speed * dt)
        self.rect.x = max(0, min(self.rect.x, w - self.rect.width))
        if self.has_shield:
            self.shield_time_left = max(0.0, self.shield_time_left - dt)
            if self.shield_time_left == 0: self.has_shield = False
        if self.magnet_time_left > 0:
            self.magnet_time_left = max(0.0, self.magnet_time_left - dt)

    def draw(self, surf):
        pygame.draw.rect(surf, BLUE, self.rect, border_radius=8)
        if self.has_shield:
            r = self.rect.inflate(16,16); pygame.draw.rect(surf, OK, r, width=2, border_radius=12)
        if self.magnet_time_left > 0:
            r = self.rect.inflate(26,26); pygame.draw.rect(surf, ORANGE, r, width=1, border_radius=14)

class Bomb:
    __slots__ = ("rect","vy")
    def __init__(self, x, vy):
        self.rect = pygame.Rect(x, -BOMB_SIZE, BOMB_SIZE, BOMB_SIZE)
        self.vy = vy
    def update(self, dt, slow=1.0): self.rect.y += int(self.vy * slow * dt)
    def draw(self, surf): pygame.draw.rect(surf, DANGER, self.rect, border_radius=6)

class Coin:
    __slots__ = ("x","y","vx","vy","r")
    def __init__(self, x):
        self.x = float(x); self.y = float(-18)
        self.vx = 0.0; self.vy = COIN_VY; self.r = 10
    @property
    def rect(self): return pygame.Rect(int(self.x - self.r), int(self.y - self.r), self.r*2, self.r*2)
    def update(self, dt, player_center=None, magnet=False):
        ax=ay=0.0
        if magnet and player_center:
            px, py = player_center
            dx, dy = px - self.x, py - self.y
            dist = max(1.0, (dx*dx + dy*dy) ** 0.5)
            ax += COIN_MAGNET_ACCEL * dx / dist
            ay += COIN_MAGNET_ACCEL * dy / dist
        self.vx += ax*dt; self.vy += ay*dt
        speed = (self.vx*self.vx + self.vy*self.vy) ** 0.5
        if speed > COIN_MAX_SPEED:
            k = COIN_MAX_SPEED / speed; self.vx*=k; self.vy*=k
        if not magnet: self.vy = max(self.vy, COIN_VY)
        self.x += self.vx*dt; self.y += self.vy*dt
    def draw(self, surf):
        pygame.draw.circle(surf, GOLD, (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(surf, (255,230,120), (int(self.x), int(self.y)), self.r, width=2)

class PowerUp:
    TYPES = ("shield", "slow", "clear", "magnet")
    COLORS = {"shield": OK, "slow": ORANGE, "clear": PURPLE, "magnet": (90, 200, 255)}
    def __init__(self, kind, x, vy=150):
        self.kind = kind
        self.rect = pygame.Rect(x, -26, 26, 26)
        self.vy = vy
    def update(self, dt): self.rect.y += int(self.vy * dt)
    def apply(self, game):
        if self.kind == "shield":
            game.player.has_shield = True
            game.player.shield_time_left = SHIELD_TIME + 2*save.upgrades.get("shield",0)
        elif self.kind == "slow":
            game.slow_time_left = SLOW_TIME
        elif self.kind == "clear":
            if game.bombs:
                for b in game.bombs: game.pop_particles(b.rect.centerx, b.rect.centery, color=PURPLE)
            game.bombs.clear()
        elif self.kind == "magnet":
            game.player.magnet_time_left = MAGNET_TIME + 2*save.upgrades.get("magnet",0)
    def draw(self, surf):
        c = self.COLORS[self.kind]
        pygame.draw.ellipse(surf, c, self.rect)
        if self.kind == "clear":
            text(BOMB_CLEAN_LABEL, self.rect.centerx, self.rect.centery-10, (255,255,255), center=True)

class Game:
    def __init__(self):
        self.reset_full()
        self.best_time = save.best
        self.coins_collected = 0

    def reset_full(self):
        self.apply_diff_profile()
        self.player = Player()
        self.bombs = []; self.powerups = []; self.particles = []; self.coins = []
        self.time_alive = 0.0; self.diff_timer = 0.0
        self.state = "MENU"  
        self.slow_time_left = 0.0
        self.coins_collected = 0
        pygame.time.set_timer(NEW_BOMB, 0); pygame.time.set_timer(NEW_PWR, 0); pygame.time.set_timer(NEW_COIN, 0)

    def apply_diff_profile(self):
        prof = DIFF_PROFILES.get(save.difficulty, DIFF_PROFILES["Normal"])
        self.BOMB_SPEED0 = prof["BOMB_SPEED0"]; self.SPAWN_MS0 = prof["SPAWN_MS0"]
        self.SPAWN_MIN_MS= prof["SPAWN_MIN_MS"]; self.STEP_V   = prof["STEP_V"]; self.STEP_SPAWN = prof["STEP_SPAWN"]
        self.bomb_speed = self.BOMB_SPEED0; self.spawn_ms = self.SPAWN_MS0

    def start(self):
        self.apply_diff_profile()
        self.player = Player()
        self.bombs.clear(); self.powerups.clear(); self.particles.clear(); self.coins.clear()
        self.time_alive = 0.0; self.diff_timer = 0.0
        self.slow_time_left = 0.0; self.coins_collected = 0
        self.state = "RUNNING"
        pygame.time.set_timer(NEW_BOMB, self.spawn_ms)
        drop_bonus = save.upgrades.get("drops",0)
        lo, hi = POWERUP_MS
        hi = max(hi - 600*drop_bonus, lo+400)
        pygame.time.set_timer(NEW_PWR, random.randint(lo, hi))
        pygame.time.set_timer(NEW_COIN, COIN_MS)

    def pop_particles(self, x, y, count=10, color=DANGER):
        for _ in range(count): self.particles.append(Particle(x, y, color))

    def bump_difficulty(self):
        self.bomb_speed += self.STEP_V
        self.spawn_ms = max(self.SPAWN_MIN_MS, self.spawn_ms - self.STEP_SPAWN)
        pygame.time.set_timer(NEW_BOMB, self.spawn_ms)

    def update(self, dt):
        if self.state != "RUNNING": return
        slow_factor = SLOW_FACTOR if self.slow_time_left > 0 else 1.0
        if self.slow_time_left > 0: self.slow_time_left = max(0.0, self.slow_time_left - dt)
        self.player.update(dt)
        for b in self.bombs: b.update(dt, slow=slow_factor)
        for p in self.powerups: p.update(dt)
        magnet_on = self.player.magnet_time_left > 0
        pc = self.player.rect.center
        for c in self.coins: c.update(dt, player_center=pc, magnet=magnet_on)
        for pr in self.particles: pr.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        w, h = screen.get_size()
        self.bombs    = [b for b in self.bombs if b.rect.top < h]
        self.powerups = [p for p in self.powerups if p.rect.top < h]
        self.coins    = [c for c in self.coins if c.y - c.r < h]

        for b in list(self.bombs):
            if b.rect.colliderect(self.player.rect):
                if self.player.has_shield:
                    self.player.has_shield = False; self.player.shield_time_left = 0.0
                    self.bombs.remove(b); self.pop_particles(b.rect.centerx, b.rect.centery, color=OK)
                elif self.player.second_chance_available:
                    self.player.second_chance_available = False
                    self.bombs.remove(b); self.pop_particles(b.rect.centerx, b.rect.centery, color=(80,80,80))
                else:
                    self.state = "GAME_OVER"
                    self.best_time = max(self.best_time, self.time_alive)
                    save.best = self.best_time
                    save.coins_total += self.coins_collected
                    save_save(save)
                    pygame.time.set_timer(NEW_BOMB, 0); pygame.time.set_timer(NEW_PWR, 0); pygame.time.set_timer(NEW_COIN, 0)
                break
        for p in list(self.powerups):
            if p.rect.colliderect(self.player.rect):
                p.apply(self); self.powerups.remove(p)
                self.pop_particles(p.rect.centerx, p.rect.centery, color=PowerUp.COLORS[p.kind])
        for c in list(self.coins):
            if c.rect.colliderect(self.player.rect):
                self.coins.remove(c); self.coins_collected += 1
                self.pop_particles(int(c.x), int(c.y), color=GOLD)

        self.time_alive += dt; self.diff_timer += dt
        if self.diff_timer >= DIFF_EVERY_S:
            self.diff_timer = 0.0; self.bump_difficulty()

    def draw_hud(self):
        w, _ = screen.get_size()
        pygame.draw.rect(screen, (255,255,255,180), (0,0,w,64))
        pygame.draw.line(screen, OUTLINE, (0,64), (w,64), width=1)
        text(f"Time: {self.time_alive:.1f}s", 16, 14)
        text(f"Best: {self.best_time:.1f}s", 16, 36, MUTED)
        text(f"Coins: {self.coins_collected}", w-150, 14, (120,95,0))
        if self.slow_time_left > 0: text(f"Slow {self.slow_time_left:.1f}s", w-150, 36, WARN)
        if self.player.has_shield:  text("Shield", w-260, 36, OK)
        if self.player.magnet_time_left > 0: text(f"Magnet {self.player.magnet_time_left:.1f}s", w-260, 14, (90,200,255))

    def draw(self):
        draw_gradient_bg(screen)
        for b in self.bombs: b.draw(screen)
        for p in self.powerups: p.draw(screen)
        for c in self.coins: c.draw(screen)
        self.player.draw(screen)
        for pr in self.particles: pr.draw(screen)
        self.draw_hud()

        if self.state == "PAUSED":
            self.draw_center_message("PAUSED", "Press P to resume")
        if self.state == "GAME_OVER":
            self.draw_center_message("GAME OVER", f"Coins: {self.coins_collected}   R — restart   Esc — menu", color=DANGER)

    def draw_center_message(self, title, subtitle, color=TEXT):
        w, h = screen.get_size()
        panel = pygame.Rect(w//2-220, h//2-90, 440, 180)
        rounded_panel(panel)
        text(title, panel.centerx, panel.y+36, color, big=True, center=True)
        text(subtitle, panel.centerx, panel.y+100, MUTED, center=True)

    def spawn_bomb(self):
        w, _ = screen.get_size()
        x = random.randint(0, w - BOMB_SIZE)
        self.bombs.append(Bomb(x, self.bomb_speed))

    def spawn_powerup(self):
        w, _ = screen.get_size()
        kind = random.choice(PowerUp.TYPES)
        x = random.randint(24, w - 50)
        self.powerups.append(PowerUp(kind, x))
        drop_bonus = save.upgrades.get("drops",0)
        lo, hi = POWERUP_MS
        hi = max(hi - 600*drop_bonus, lo+400)
        pygame.time.set_timer(NEW_PWR, random.randint(lo, hi))

    def spawn_coin(self):
        w, _ = screen.get_size()
        x = random.randint(20, w - 20)
        self.coins.append(Coin(x))

SHOP_ITEMS = [
    ("shield", "Shield+", "Shield lasts +2s per level", 3, 15, 10),
    ("magnet", "Magnet+", "Magnet lasts +2s per level", 3, 15, 10),
    ("drops",  "Drops+",  "Power-ups drop more often",   3, 20, 12),
    ("second", "Second Chance", "One extra life per run", 1, 40, 0),
]

def upgrade_cost(key, lvl):
    _,_,_,max_lvl, base, step = next(x for x in SHOP_ITEMS if x[0]==key)
    if lvl>=max_lvl: return None
    return base + step*lvl

def draw_menu(game, WIDTH, HEIGHT):
    draw_gradient_bg(screen)
    panel_w = min(520, WIDTH - 40)
    panel_h = min(520, HEIGHT - 140)
    panel = pygame.Rect((WIDTH-panel_w)//2, (HEIGHT-panel_h)//2, panel_w, panel_h)
    rounded_panel(panel)

    text("DODGE!", panel.centerx, panel.y+36, big=True, center=True)
    text("← → to move   Enter to start", panel.centerx, panel.y+110, MUTED, center=True)
    text("S = Settings   H = Shop   Esc = Quit", panel.centerx, panel.y+140, MUTED, center=True)

    text(f"Best: {game.best_time:.1f}s", panel.x+32, panel.y+190, mid=True)
    text(f"Coins: {save.coins_total}", panel.x+32, panel.y+222, (120,95,0), mid=True)

    text("Power-ups: Shield / Slow / Ω Clear / U Magnet", panel.centerx, panel.y+270, MUTED, center=True)

    mpos = pygame.mouse.get_pos()
    gap = 54
    y0 = panel.y + panel.h - (4*46 + 3*12) - 28
    btn_start   = Button(pygame.Rect(panel.centerx-110, y0,           220, 46), "START (Enter)")
    btn_settings= Button(pygame.Rect(panel.centerx-110, y0+gap,       220, 46), "Settings (S)", "ghost")
    btn_shop    = Button(pygame.Rect(panel.centerx-110, y0+2*gap,     220, 46), "Shop (H)", "ghost")
    btn_exit    = Button(pygame.Rect(panel.centerx-110, y0+3*gap,     220, 46), "Exit (Esc)", "danger")
    for b in (btn_start, btn_settings, btn_shop, btn_exit): b.draw(mpos)

    return {"start":btn_start, "settings":btn_settings, "shop":btn_shop, "exit":btn_exit}

def draw_settings(WIDTH, HEIGHT):
    draw_gradient_bg(screen)
    panel_w = min(520, WIDTH - 40)
    panel_h = 420
    panel = pygame.Rect((WIDTH-panel_w)//2, (HEIGHT-panel_h)//2, panel_w, panel_h)
    rounded_panel(panel)
    text("SETTINGS", panel.centerx, panel.y+36, big=True, center=True)

    mpos = pygame.mouse.get_pos()
    text("Difficulty", panel.x+36, panel.y+120, MUTED)
    sel = Select(pygame.Rect(panel.right-220, panel.y+110, 180, 36), ["Easy","Normal","Hard"],
                 ["Easy","Normal","Hard"].index(save.difficulty))
    sel.draw(mpos)

    text("Volume", panel.x+36, panel.y+178, MUTED)
    slider = Slider(pygame.Rect(panel.right-220, panel.y+170, 180, 36), save.volume/100.0)
    slider.draw(mpos)

    text("Fullscreen", panel.x+36, panel.y+236, MUTED)
    fs_btn = Button(pygame.Rect(panel.right-220, panel.y+228, 180, 36), "Toggle", "ghost")
    fs_btn.draw(mpos)

    back = Button(pygame.Rect(panel.centerx-90, panel.bottom-64, 180, 44), "Back (Esc)")
    back.draw(mpos)

    return {"select":sel, "slider":slider, "fs":fs_btn, "back":back}

def draw_shop(WIDTH, HEIGHT):
    draw_gradient_bg(screen)
    panel_w = min(540, WIDTH - 40)
    panel_h = min(560, HEIGHT - 120)
    panel = pygame.Rect((WIDTH-panel_w)//2, (HEIGHT-panel_h)//2, panel_w, panel_h)
    rounded_panel(panel)
    text("SHOP", panel.centerx, panel.y+36, big=True, center=True)
    text(f"Coins: {save.coins_total}", panel.x+32, panel.y+84, (120,95,0), mid=True)

    mpos = pygame.mouse.get_pos()
    buttons = {}
    y = panel.y + 120
    card_h = 92
    for key,title,desc,max_lvl,_,_ in SHOP_ITEMS:
        lvl = save.upgrades.get(key,0)
        card = pygame.Rect(panel.x+20, y, panel.w-40, card_h)
        rounded_panel(card, radius=12, shadow=False)
        text(f"{title}  (Lv {lvl}/{max_lvl})", card.x+16, card.y+12, mid=True)
        text(desc, card.x+16, card.y+48, MUTED)

        cost = upgrade_cost(key, lvl)
        label = "MAXED" if cost is None else f"Buy — {cost}c"
        kind = "ghost" if cost is None or cost>save.coins_total else "primary"
        btn = Button(pygame.Rect(card.right-140, card.y+24, 120, 42), label, kind)
        btn.draw(mpos)
        buttons[key] = (btn, cost)
        y += card_h + 12

    back = Button(pygame.Rect(panel.centerx-90, panel.bottom-60, 180, 44), "Back (Esc)")
    back.draw(mpos)
    buttons["back"] = (back, None)
    return buttons

def main():
    global screen
    game = Game()
    ui_cache = {}

    while True:
        dt = clock.tick(FPS) / 1000.0
        WIDTH, HEIGHT = screen.get_size()
        mpos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if game.state == "MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER): game.start()
                    elif event.key == pygame.K_s: game.state = "SETTINGS"
                    elif event.key == pygame.K_h: game.state = "SHOP"
                    elif event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button==1 and ui_cache:
                    if ui_cache["start"].clicked(event): game.start()
                    elif ui_cache["settings"].clicked(event): game.state = "SETTINGS"
                    elif ui_cache["shop"].clicked(event): game.state = "SHOP"
                    elif ui_cache["exit"].clicked(event): pygame.quit(); sys.exit()

            elif game.state == "SETTINGS":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    game.state = "MENU"
                if ui_cache:
                    ui_cache["slider"].handle(event)
                    if ui_cache["fs"].clicked(event):
                        screen = toggle_fullscreen()
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button==1:
                        ui_cache["select"].handle(event)
                        if ui_cache["back"].clicked(event): game.state = "MENU"
                save.volume = int(round((ui_cache["slider"].value if ui_cache else save.volume/100.0)*100))
                pygame.mixer.music.set_volume(save.volume/100.0)
                opts = ["Easy","Normal","Hard"]
                save.difficulty = opts[ui_cache["select"].selected] if ui_cache else save.difficulty
                save_save(save)

            elif game.state == "SHOP":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    game.state = "MENU"
                if ui_cache and event.type == pygame.MOUSEBUTTONDOWN and event.button==1:
                    if ui_cache["back"][0].clicked(event):
                        game.state = "MENU"
                    else:
                        for key in ("shield","magnet","drops","second"):
                            btn, cost = ui_cache[key]
                            if cost is not None and btn.clicked(event) and save.coins_total >= cost:
                                save.coins_total -= cost
                                save.upgrades[key] = min(save.upgrades.get(key,0)+1,
                                                         next(x[3] for x in SHOP_ITEMS if x[0]==key))
                                save_save(save)

            elif game.state in ("RUNNING","PAUSED","GAME_OVER"):
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p and game.state == "RUNNING": game.state = "PAUSED"
                    elif event.key == pygame.K_p and game.state == "PAUSED": game.state = "RUNNING"
                    elif event.key == pygame.K_r and game.state == "GAME_OVER": game.start()
                    elif event.key == pygame.K_ESCAPE: game.reset_full()
                    elif event.key == pygame.K_f: screen = toggle_fullscreen()
                if event.type == NEW_BOMB and game.state == "RUNNING": game.spawn_bomb()
                if event.type == NEW_PWR  and game.state == "RUNNING": game.spawn_powerup()
                if event.type == NEW_COIN and game.state == "RUNNING": game.spawn_coin()

        if game.state == "MENU":
            ui_cache = draw_menu(game, WIDTH, HEIGHT)
        elif game.state == "SETTINGS":
            ui_cache = draw_settings(WIDTH, HEIGHT)
        elif game.state == "SHOP":
            ui_cache = draw_shop(WIDTH, HEIGHT)
        elif game.state == "RUNNING":
            ui_cache = {}
            game.update(dt); game.draw()
        elif game.state == "PAUSED":
            ui_cache = {}; game.draw()
        elif game.state == "GAME_OVER":
            ui_cache = {}; game.draw()

        pygame.display.flip()

if __name__ == "__main__":
    main()
