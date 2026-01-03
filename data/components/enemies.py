__author__ = 'justinarmstrong'

import pygame as pg
from .. import setup
from .. import constants as c
from .mario import Mario
from .powerups import *


class Enemy(pg.sprite.Sprite):
    """Base class for all enemies (Goombas, Koopas, etc.)"""
    def __init__(self):
        pg.sprite.Sprite.__init__(self)

    def setup_enemy(self, x, y, direction, name, setup_frames):
        """Sets up enemy attributes"""
        self.sprite_sheet = setup.GFX.get('smb_enemies_sheet', pg.Surface((32, 32)))
        self.frames = []
        self.frame_index = 0
        self.animate_timer = 0
        self.death_timer = 0
        self.gravity = 1.5
        self.state = c.WALK
        self.name = name
        self.direction = direction

        # 允许 setup_frames 为 None
        if setup_frames:
            setup_frames()

        self.image = self.frames[self.frame_index] if self.frames else pg.Surface((16, 16))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.bottom = y
        self.set_velocity()

    def set_velocity(self):
        self.x_vel = -2 if self.direction == c.LEFT else 2
        self.y_vel = 0

    def get_image(self, x, y, width, height):
        image = pg.Surface([width, height]).convert()
        rect = image.get_rect()
        image.blit(self.sprite_sheet, (0, 0), (x, y, width, height))
        image.set_colorkey(c.BLACK)
        image = pg.transform.scale(image,
                                   (int(rect.width * c.SIZE_MULTIPLIER),
                                    int(rect.height * c.SIZE_MULTIPLIER)))
        return image

    def handle_state(self):
        if self.state == c.WALK:
            self.walking()
        elif self.state == c.FALL:
            self.falling()
        elif self.state == c.JUMPED_ON:
            self.jumped_on()
        elif self.state == c.SHELL_SLIDE:
            self.shell_sliding()
        elif self.state == c.DEATH_JUMP:
            self.death_jumping()

    def walking(self):
        if (self.current_time - self.animate_timer) > 125:
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.animate_timer = self.current_time

    def falling(self):
        if self.y_vel < 10:
            self.y_vel += self.gravity

    def jumped_on(self):
        pass

    def shell_sliding(self):
        pass

    def death_jumping(self):
        self.rect.y += self.y_vel
        self.rect.x += self.x_vel
        self.y_vel += self.gravity
        if self.rect.y > 600:
            self.kill()

    def start_death_jump(self, direction):
        self.y_vel = -8
        self.x_vel = 2 if direction == c.RIGHT else -2
        self.gravity = 0.5
        self.frame_index = 3
        self.image = self.frames[self.frame_index]
        self.state = c.DEATH_JUMP

    def animation(self):
        if self.frames:
            self.image = self.frames[self.frame_index]

    def check_collision(self, platforms):
        """自动转向逻辑"""
        # Y方向
        self.rect.y += self.y_vel
        collisions = pg.sprite.spritecollide(self, platforms, False)
        for sprite in collisions:
            if self.y_vel > 0:
                self.rect.bottom = sprite.rect.top
                self.y_vel = 0
                self.state = c.WALK
            elif self.y_vel < 0:
                self.rect.top = sprite.rect.bottom
                self.y_vel = 0

        # X方向
        self.rect.x += self.x_vel
        collisions = pg.sprite.spritecollide(self, platforms, False)
        for sprite in collisions:
            if self.x_vel > 0:
                self.rect.right = sprite.rect.left
                self.x_vel *= -1
                self.direction = c.LEFT
            elif self.x_vel < 0:
                self.rect.left = sprite.rect.right
                self.x_vel *= -1
                self.direction = c.RIGHT

    def update(self, game_info, platforms=None, *args):
        self.current_time = game_info[c.CURRENT_TIME] if game_info else 0

        # 检查死亡状态
        if self.state == c.JUMPED_ON:
            if hasattr(self, 'death_timer') and (self.current_time - self.death_timer) > 500:
                self.kill()
                return

        if platforms:
            self.check_collision(platforms)
        else:
            self.rect.x += self.x_vel
            self.rect.y += self.y_vel
            self.y_vel += self.gravity

        self.handle_state()
        self.animation()


# ------------------- Goomba -------------------
# ------------------- Goomba -------------------
class Goomba(Enemy):
    def __init__(self, y=c.GROUND_HEIGHT, x=0, direction=c.LEFT, name='goomba'):
        super().__init__()
        self.setup_enemy(x, y, direction, name, self.setup_frames)

    def setup_frames(self):
        self.frames.append(self.get_image(0, 4, 16, 16))
        self.frames.append(self.get_image(30, 4, 16, 16))
        self.frames.append(self.get_image(61, 0, 16, 16))
        self.frames.append(pg.transform.flip(self.frames[1], False, True))

    def jumped_on(self):
        self.frame_index = 2


    def update(self, game_info, platforms=None, *args):
        """重写update方法以接受platforms参数"""
        # 调用父类的update方法，但确保platforms参数被传递
        super().update(game_info, platforms, *args)


# ------------------- Koopa -------------------
class Koopa(Enemy):
    def __init__(self, y=c.GROUND_HEIGHT, x=0, direction=c.LEFT, name='koopa'):
        super().__init__()
        self.setup_enemy(x, y, direction, name, self.setup_frames)

    def setup_frames(self):
        self.frames.append(self.get_image(150, 0, 16, 24))
        self.frames.append(self.get_image(180, 0, 16, 24))
        self.frames.append(self.get_image(360, 5, 16, 15))
        self.frames.append(pg.transform.flip(self.frames[2], False, True))

    def jumped_on(self):
        self.x_vel = 0
        self.frame_index = 2
        shell_y = self.rect.bottom
        shell_x = self.rect.x
        self.rect = self.frames[self.frame_index].get_rect()
        self.rect.x = shell_x
        self.rect.bottom = shell_y

    def shell_sliding(self):
        self.x_vel = 10 if self.direction == c.RIGHT else -10

    def update(self, game_info, platforms=None, *args):
        """重写update方法以接受platforms参数"""
        # 调用父类的update方法，但确保platforms参数被传递
        super().update(game_info, platforms, *args)


# ------------------- Boss -------------------
class boss(Enemy):
    def __init__(self, y=c.GROUND_HEIGHT, x=0, direction=c.LEFT, name='smart_enemy'):
        super().__init__()

        self.current_time = 0
        self.direction = direction
        self.name = name

        # 动画相关
        self.animation_state = 'idle'
        self.current_animation = []
        self.frame_index = 0
        self.animate_timer = 0
        self.animation_once = False
        self.prev_state = None
        self.prev_direction = None
        self.frames = [pg.Surface((1, 1), pg.SRCALPHA)]
        self.all_frames = {}
        self.frame_durations = {'idle': 200, 'walk': 150, 'attack': 100, 'hurt': 150}

        # 初始化帧
        self.setup_frames()

        # Boss 属性
        self.health = 3
        self.attack_cooldown = 0
        self.attack_range = 200
        self.visible = True
        self.dying = False
        self.flash_count = 0
        self.max_flashes = 8
        self.state = c.WALK
        self.x_vel = 0
        self.y_vel = 0

        # Mario 踩计数
        self.mario_stomp_count = 0

        # 初始化 rect 已经生成 image
        self.rect = self.image.get_rect()
        self.initialized = False  # 初始化标志，用于第一次 update 修正 rect

        print("[Boss Init] Current Animation:", self.current_animation)

    def setup_frames(self):
        """加载 Boss 的动画帧"""
        boss_orig_width = 552
        boss_orig_height = 452

        scale_factor = 0.2  # 调小一点避免穿地
        width = int(boss_orig_width * scale_factor)
        height = int(boss_orig_height * scale_factor)

        def resize(frame):
            return pg.transform.scale(frame, (width, height))

        actions = {
            'idle': 'boss_stand',
            'walk': 'boss_walk',
            'attack': 'boss_attack',
            'hurt': 'boss_hurt'
        }

        for action, sheet_name in actions.items():
            if sheet_name not in setup.GFX:
                print(f"[Boss Debug] Missing sprite sheet: {sheet_name}")
                continue
            self.sprite_sheet = setup.GFX[sheet_name]

            try:
                frame = resize(self.sprite_sheet)
            except Exception as e:
                print(f"[Boss Debug] Failed to resize frame {sheet_name}: {e}")
                frame = pg.Surface((1, 1), pg.SRCALPHA)

            # 三帧循环: 站立 - 动作 - 站立
            frames = [frame, frame, frame]
            self.all_frames[f'{action}_left'] = frames
            self.all_frames[f'{action}_right'] = [pg.transform.flip(f, True, False) for f in frames]

        # 设置默认动画
        self.set_animation('idle', once=False)
        self.image = self.current_animation[self.frame_index]

    def set_animation(self, state, once=False):
        direction_str = 'left' if self.direction == c.LEFT else 'right'
        key = f"{state}_{direction_str}"

        if key not in self.all_frames:
            print(f"[Boss Debug] Animation key missing: {key}")
            return

        if self.animation_state != state or self.prev_direction != direction_str:
            self.current_animation = self.all_frames[key]
            self.animation_state = state
            self.frame_index = 0
            self.animate_timer = self.current_time
            self.animation_once = once
            self.prev_state = state
            self.prev_direction = direction_str
            self.image = self.current_animation[self.frame_index]

            print(f"[Boss Debug] Animation set: {key}, frames: {len(self.current_animation)}")

    def update(self, game_info, platforms=None, *args):
            """修改update方法签名，与其他敌人类保持一致"""
            self.current_time = game_info[c.CURRENT_TIME] if game_info else 0

            # 第一次初始化 rect 底部在地面
            if not self.initialized and hasattr(self, 'level'):
                self.rect.bottom = self.level.level_height - 60
                self.y_vel = 0
                self.initialized = True

            if self.dying:
                self.animation()
                return

            # 处理平台碰撞
            if platforms:
                self.apply_gravity(platforms)
            else:
                # 如果没有提供平台，使用默认的重力
                self.rect.x += self.x_vel
                self.rect.y += self.y_vel
                self.y_vel += 0.5  # 默认重力

            self.handle_state()
            self.animation()

    def handle_state(self):
        if self.dying:
            return
        if self.state == c.WALK:
            self.walking()
        elif self.state == c.ATTACK:
            self.attacking()
        elif self.state == c.HURT:
            self.hurt()
        else:
            self.idle()

    def walking(self):
        if hasattr(self, 'level') and hasattr(self.level, 'mario'):
            mario_obj = self.level.mario
            self.direction = c.RIGHT if mario_obj.rect.centerx > self.rect.centerx else c.LEFT
            distance = mario_obj.rect.centerx - self.rect.centerx
            direction_sign = 1 if distance > 0 else -1
            distance_abs = abs(distance)
            max_speed = 4
            min_speed = 2
            speed = min(max_speed, max(min_speed, distance_abs / 50))
            self.x_vel = speed * direction_sign
            self.rect.x += self.x_vel
            if distance_abs < self.attack_range and self.current_time >= self.attack_cooldown:
                self.state = c.ATTACK
                self.set_animation('attack', once=True)
                return
        self.set_animation('walk', once=False)

    def attacking(self):
        if hasattr(self, 'level') and hasattr(self.level, 'mario'):
            mario_obj = self.level.mario
            self.direction = c.RIGHT if mario_obj.rect.centerx > self.rect.centerx else c.LEFT
            self.rect.x += 1 if self.direction == c.RIGHT else -1
        self.set_animation('attack', once=True)

    def hurt(self):
        self.set_animation('hurt', once=True)

    def idle(self):
        self.set_animation('idle', once=False)
        self.x_vel = 0

    def receive_damage(self, dmg=1):
        if self.dying:
            return
        self.health -= dmg
        self.state = c.HURT
        self.set_animation('hurt', once=True)
        self.attack_cooldown = self.current_time + 800
        if self.health <= 0:
            self.start_dying()

    def start_dying(self):
        self.dying = True
        self.flash_count = 0
        self.visible = True
        self.x_vel = 0
        self.y_vel = 0
        self.animate_timer = self.current_time

    def animation(self):
        if not self.current_animation:
            return

        if self.dying:
            if (self.current_time - self.animate_timer) > 120:
                self.visible = not self.visible
                self.animate_timer = self.current_time
                self.flash_count += 1
                if self.flash_count >= self.max_flashes:
                    self.kill()
                    print("[Boss Debug] Boss died")
                    return
            frame = self.current_animation[self.frame_index]
            self.image = frame.copy()
            self.image.set_alpha(255 if self.visible else 0)
            return

        duration = self.frame_durations.get(self.animation_state, 150)

        if self.animation_once:
            if (self.current_time - self.animate_timer) > duration:
                if self.frame_index < len(self.current_animation) - 1:
                    self.frame_index += 1
                    self.animate_timer = self.current_time
                else:
                    self.animation_once = False
                    if self.state in [c.ATTACK, c.HURT]:
                        self.state = c.WALK
                        self.set_animation('walk', once=False)
        else:
            if (self.current_time - self.animate_timer) > duration:
                self.frame_index = (self.frame_index + 1) % len(self.current_animation)
                self.animate_timer = self.current_time

        self.image = self.current_animation[self.frame_index]

    def on_mario_stomp(self):
        self.mario_stomp_count += 1
        self.set_animation('hurt', once=True)
        print(f"[Boss Debug] Mario stomped boss. Count: {self.mario_stomp_count}")

    def apply_gravity(self, platforms):
        if self.dying:
            return
        self.y_vel += 0.5
        self.rect.y += self.y_vel
        collision = pg.sprite.spritecollideany(self, platforms)
        if collision:
            self.rect.bottom = collision.rect.top
            self.y_vel = 0