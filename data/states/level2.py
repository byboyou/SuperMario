from __future__ import division

import os
import pickle
import random

import pygame as pg
from .. import setup, tools
from .. import constants as c
from .. import game_sound
from ..components import mario
from ..components import collider
from ..components import bricks
from ..components import coin_box
from ..components import enemies
from ..components import checkpoint
from ..components import flagpole
from ..components import info
from ..components import score
from ..components import castle_flag
from ..components import boss as boss_module
from ..components.powerups import Mushroom  # Powerup 蘑菇
from ..components.enemies import *


class Level2(tools._State):
    def __init__(self):
        tools._State.__init__(self)

        # 随机地形
        self.random_terrain_group = pg.sprite.Group()
        self.last_terrain_generation_time = 0
        self.terrain_generation_interval = 10000
        self.max_terrain_blocks = 10
        self.terrain_block_size = 40

        # Boss 相关计时
        self.last_boss_check_time = 0
        self.boss_check_interval = 10000  # 每 5 秒检测一次

        # 固定砖块组
        self.fixed_terrain_group = pg.sprite.Group()
        
        # 截图相关属性（新增）
        self.screenshot_count = 0

            
    def take_screenshot(self, surface=None):
        """截图并保存到pictures文件夹"""
        # 获取当前文件所在目录的父级目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        pictures_dir = os.path.join(parent_dir, 'pictures')
    
        # 如果pictures目录不存在，则创建它
        if not os.path.exists(pictures_dir):
            os.makedirs(pictures_dir)
    
        # 生成截图文件名（包含时间戳和计数器）
        timestamp = pg.time.get_ticks()
        self.screenshot_count += 1
        filename = f"screenshot_{self.screenshot_count}_{timestamp}.png"
        filepath = os.path.join(pictures_dir, filename)
    
        # 保存截图
        try:
            pg.image.save(surface, filepath)
            print(f"screenshot saved: {filepath}")

        except Exception as e:
            print(f"截图保存失败: {e}")
            
    def update(self, surface, keys, current_time):
        self.game_info[c.CURRENT_TIME] = self.current_time = current_time
        self.update_random_terrain(current_time)
        self.handle_states(keys)
        self.check_boss_spawn_logic()
        self.check_if_time_out()
        self.blit_everything(surface)
        self.sound_manager.update(self.game_info, self.mario)

        # 检查截图快捷键 F12（新增）
        if keys[pg.K_g]:
            self.take_screenshot(surface)

    # ------------------------------------------------------------------
    def startup(self, current_time, persist):
        self.game_info = persist
        self.persist = self.game_info
        self.game_info[c.CURRENT_TIME] = current_time
        self.game_info[c.LEVEL_STATE] = c.NOT_FROZEN
        self.game_info[c.MARIO_DEAD] = False

        self.state = c.NOT_FROZEN
        self.death_timer = 0

        self.random_terrain_group.empty()
        self.fixed_terrain_group.empty()  # 清空固定砖块组
        self.last_terrain_generation_time = current_time

        self.moving_score_list = []
        self.overhead_info_display = info.OverheadInfo(self.game_info, c.LEVEL)
        self.sound_manager = game_sound.Sound(self.overhead_info_display)

        self.setup_background()
        self.setup_ground()
        self.setup_mario()
        self.setup_fixed_terrain()  # 设置固定砖块
        self.setup_spritegroups()

    # ------------------------------------------------------------------
    def setup_fixed_terrain(self):
        """在较低高度设置固定砖块，Mario可以直接跳上去"""
        # 设置砖块高度（比原来低，Mario可以直接跳上去）
        fixed_height = self.level_height - 200  # 离地面200像素，Mario可以轻松跳上去
        brick_width = 40
        brick_height = 40
        
        # 设置砖块出现的x轴范围（中间区域）
        start_x = self.level_width // 4
        end_x = self.level_width * 3 // 4
        
        # 生成5-8个固定砖块
        num_bricks = 8
        
        # 计算每个砖块的间距
        total_space = end_x - start_x
        spacing = total_space // (num_bricks + 1)
        
        # 生成固定砖块
        for i in range(num_bricks):
            x = start_x + (i + 1) * spacing
            y = fixed_height
            
            # 创建砖块
            brick = bricks.Brick(x, y)
            self.fixed_terrain_group.add(brick)

    # ------------------------------------------------------------------
    def setup_background(self):
        self.background = setup.GFX['level_2']
        self.back_rect = self.background.get_rect()

        screen_info = pg.display.Info()
        screen_width = screen_info.current_w
        screen_height = screen_info.current_h

        target_height = screen_height - 100
        target_width = int(target_height * 1.5)

        if target_width > screen_width:
            target_width = screen_width
            target_height = int(target_width * 2 / 3)

        self.background = pg.transform.scale(self.background,
                                             (target_width, target_height))
        self.back_rect = self.background.get_rect()

        self.level_width = self.back_rect.width
        self.level_height = self.back_rect.height

        self.level = pg.Surface((self.level_width, self.level_height)).convert()
        self.level_rect = self.level.get_rect()
        self.viewport = setup.SCREEN.get_rect(bottom=self.level_rect.bottom)
        self.viewport.x = self.game_info[c.CAMERA_START_X]

    # ------------------------------------------------------------------
    def setup_ground(self):
        ground_y = self.level_height - 60
        ground_rect = collider.Collider(0, ground_y,
                                        self.level_width, 60)
        self.ground_group = pg.sprite.Group(ground_rect)

    # ------------------------------------------------------------------
    def setup_mario(self):
        self.mario = Mario()
        self.mario.rect.x = 50
        self.mario.rect.bottom = self.level_height - 60

    # ------------------------------------------------------------------
    def setup_spritegroups(self):
        """设置精灵组"""
        # 将固定砖块和地面都添加到碰撞组
        self.ground_step_pipe_group = pg.sprite.Group(self.ground_group)
        self.ground_step_pipe_group.add(self.fixed_terrain_group)
        
        # 创建专门的敌人组
        self.enemy_group = pg.sprite.Group()
        self.sprites_about_to_die_group = pg.sprite.Group()
        # 删除龟壳组，因为乌龟死后直接移除
        # self.shell_group = pg.sprite.Group()

        # Boss
        self.boss = boss_module.boss()
        self.boss.level = self
        self.boss.setup_frames()

        # Boss 初始位置
        ground_y = self.level_height - 60
        self.boss.rect.bottom = ground_y
        self.boss.rect.right = self.level_width - 20
        self.boss.y_vel = 0

        # Mario + Boss + 敌人组
        self.mario_and_enemy_group = pg.sprite.Group(
            self.mario,
            self.boss
        )

    # ------------------------------------------------------------------
    # 随机地形生成（修改为避开固定砖块区域）
    # ------------------------------------------------------------------
    def generate_random_terrain(self):
        self.random_terrain_group.empty()
        existing_blocks = []

        # 固定砖块区域（中间区域）
        fixed_start_x = self.level_width // 4
        fixed_end_x = self.level_width * 3 // 4
        fixed_height = self.level_height - 200  # 与setup_fixed_terrain中的高度保持一致

        num_blocks = random.randint(3, self.max_terrain_blocks)
        attempts = 0

        while len(self.random_terrain_group) < num_blocks and attempts < 50:
            attempts += 1

            x = random.randint(50, self.level_width - 80)
            y = random.randint(100, self.level_height - 120)

            # 避开固定砖块区域
            if fixed_start_x <= x <= fixed_end_x and abs(y - fixed_height) < 100:
                continue

            rect = pg.Rect(x, y,
                           self.terrain_block_size,
                           self.terrain_block_size)

            if any(rect.colliderect(r) for r in existing_blocks):
                continue

            block = bricks.Brick(x, y)
            self.random_terrain_group.add(block)
            existing_blocks.append(rect)

    def update_random_terrain(self, current_time):
        if current_time - self.last_terrain_generation_time > self.terrain_generation_interval:
            self.generate_random_terrain()
            self.last_terrain_generation_time = current_time

    # ------------------------------------------------------------------
    # Level2 主更新
    # ------------------------------------------------------------------


    # ------------------------------------------------------------------
    # 检查 Boss 生成敌人逻辑
    # ------------------------------------------------------------------
    def check_boss_spawn_logic(self):
        if not self.boss.alive():
            return

        # 每 boss_check_interval 检查一次
        if (self.current_time - self.last_boss_check_time) >= self.boss_check_interval:
            self.last_boss_check_time = self.current_time

            # 检查场上敌人数量
            if len(self.enemy_group) < 2:  # 如果敌人少于2个
                # 生成 Goomba
                spawn_x = max(0, self.boss.rect.left - 50)
                spawn_y = self.boss.rect.bottom
                new_goomba = Goomba(x=spawn_x, y=spawn_y)
                new_goomba.level = self
                self.mario_and_enemy_group.add(new_goomba)
                self.enemy_group.add(new_goomba)  # 添加到敌人组

                # 生成 Koopa
                spawn_x2 = min(self.level_width - 50, self.boss.rect.right + 50)
                spawn_y2 = self.boss.rect.bottom
                new_koopa = Koopa(x=spawn_x2, y=spawn_y2)
                new_koopa.level = self
                self.mario_and_enemy_group.add(new_koopa)
                self.enemy_group.add(new_koopa)  # 添加到敌人组

                # Boss 播放攻击动画
                self.boss.state = c.ATTACK
                self.boss.attacking()

        # 检查 Mario 踩敌次数
        if self.boss.mario_stomp_count >= 4:
            self.boss.mario_stomp_count = 0
            # 在 Mario 头顶生成强化蘑菇
            spawn_x = self.mario.rect.centerx
            spawn_y = self.mario.rect.top - 16
            mushroom = Mushroom(spawn_x, spawn_y, name='enhanced_mushroom')
            self.mario_and_enemy_group.add(mushroom)

            # Boss 播放攻击动画
            self.boss.state = c.ATTACK
            self.boss.attacking()

        # ---------------- 检查小怪是否到达地图边界 ----------------
        for sprite in self.enemy_group.sprites():
            # 到达左边界反向
            if sprite.rect.left <= 0:
                sprite.rect.left = 0
                if hasattr(sprite, 'direction'):
                    sprite.direction = c.RIGHT
                if hasattr(sprite, 'x_vel'):
                    sprite.x_vel *= -1

            # 到达右边界反向
            elif sprite.rect.right >= self.level_width:
                sprite.rect.right = self.level_width
                if hasattr(sprite, 'direction'):
                    sprite.direction = c.LEFT
                if hasattr(sprite, 'x_vel'):
                    sprite.x_vel *= -1

    # ------------------------------------------------------------------
    # 更新所有精灵
    # ------------------------------------------------------------------
    def handle_states(self, keys):
        if self.state == c.FROZEN:
            self.update_during_transition_state(keys)
        elif self.state == c.NOT_FROZEN:
            self.update_all_sprites(keys)

    def update_during_transition_state(self, keys):
        self.mario.update(keys, self.game_info, pg.sprite.Group())
        for score in self.moving_score_list:
            score.update(self.moving_score_list, self.game_info)
        self.check_if_mario_in_transition_state()
        self.check_for_mario_death()
        self.overhead_info_display.update(self.game_info, self.mario)

    def update_all_sprites(self, keys):
        """更新所有精灵"""
        # Mario更新
        self.mario.update(keys, self.game_info, pg.sprite.Group())

        # 敌人和Boss更新
        for sprite in self.mario_and_enemy_group:
            if sprite == self.mario:
                continue

            if hasattr(sprite, 'state') and sprite.state == c.JUMPED_ON:
                # 如果是乌龟，直接移除
                if hasattr(sprite, 'name') and sprite.name == 'koopa':
                    sprite.kill()  # 立即杀死乌龟
                    continue

            # 使用 Enemy/Boss 自带 update 函数
            platforms_group = pg.sprite.Group(self.ground_step_pipe_group,
                                          self.random_terrain_group)
        
            # 改为使用位置参数而不是关键字参数
            sprite.update(self.game_info, platforms_group)  # 移除了 game_info= 和 platforms=

        # 更新即将死亡的精灵
        self.sprites_about_to_die_group.update(self.game_info)
        # 删除龟壳组的更新
        # self.shell_group.update(self.game_info)

        # 更新视图和HUD
        self.adjust_sprite_positions()
        self.check_boss_collision()
        self.check_generated_objects_bounds()
        self.check_if_mario_in_transition_state()
        self.check_for_mario_death()
        self.update_viewport()
        self.overhead_info_display.update(self.game_info, self.mario)

    # ------------------------------------------------------------------
    # 其他原有函数保持不变
    # ------------------------------------------------------------------
    def adjust_sprite_positions(self):
        self.adjust_mario_position()

    def adjust_mario_position(self):
        self.last_x_position = self.mario.rect.right
        self.mario.rect.x += round(self.mario.x_vel)
        self.check_mario_x_collisions()

        if not self.mario.in_transition_state:
            self.mario.rect.y += round(self.mario.y_vel)
            self.check_mario_y_collisions()

        if self.mario.rect.x < 0:
            self.mario.rect.x = 0
        elif self.mario.rect.right > self.level_width:
            self.mario.rect.right = self.level_width

    def check_mario_x_collisions(self):
        collider_obj = pg.sprite.spritecollideany(self.mario,
                                                  self.ground_step_pipe_group)
        terrain = pg.sprite.spritecollideany(self.mario,
                                             self.random_terrain_group)
        enemy = pg.sprite.spritecollideany(self.mario, self.enemy_group)  # 新增敌人碰撞检测

        if collider_obj:
            self.adjust_mario_for_x_collisions(collider_obj)
        elif terrain:
            self.adjust_mario_for_x_collisions(terrain)
        elif enemy:  # 处理敌人碰撞
            self.adjust_mario_for_x_enemy_collisions(enemy)

    def adjust_mario_for_x_collisions(self, collider_obj):
        if self.mario.rect.x < collider_obj.rect.x:
            self.mario.rect.right = collider_obj.rect.left
        else:
            self.mario.rect.left = collider_obj.rect.right
        self.mario.x_vel = 0

    def check_mario_y_collisions(self):
        ground = pg.sprite.spritecollideany(self.mario,
                                            self.ground_step_pipe_group)
        terrain = pg.sprite.spritecollideany(self.mario,
                                             self.random_terrain_group)
        enemy = pg.sprite.spritecollideany(self.mario, self.enemy_group)  # 新增敌人碰撞检测

        if ground:
            self.adjust_mario_for_y_ground_pipe_collisions(ground)
        elif terrain:
            self.adjust_mario_for_y_terrain_collisions(terrain)
        elif enemy:  # 处理敌人碰撞
            self.adjust_mario_for_y_enemy_collisions(enemy)

        self.test_if_mario_is_falling()

    def test_if_mario_is_falling(self):
        self.mario.rect.y += 1
        test_group = pg.sprite.Group(self.ground_step_pipe_group,
                                     self.random_terrain_group)
        if pg.sprite.spritecollideany(self.mario, test_group) is None:
            if self.mario.state not in (c.JUMP, c.DEATH_JUMP):
                self.mario.state = c.FALL
        self.mario.rect.y -= 1

    def check_boss_collision(self):
        if not self.boss.alive():
            return

        if self.mario.rect.colliderect(self.boss.rect):
            # 从上方踩
            if self.mario.y_vel > 0 and \
               self.mario.rect.bottom <= self.boss.rect.top + 15:
                self.boss.receive_damage(1)
                self.boss.on_mario_stomp()
                self.mario.y_vel = -10
                self.mario.state = c.JUMP
                self.mario.rect.x = 0
                self.mario.x_vel = 0
            else:
                self.mario.start_death_jump(self.game_info)

    def check_generated_objects_bounds(self):
        for sprite in self.enemy_group.sprites():  # 改为检查敌人组
            if sprite.rect.right < 0 or sprite.rect.left > self.level_width:
                sprite.kill()
        
        # 检查即将死亡的精灵
        for sprite in self.sprites_about_to_die_group:
            if sprite.rect.y > self.level_height:
                sprite.kill()

    def check_for_mario_death(self):
        if self.mario.rect.y > c.SCREEN_HEIGHT:
            self.mario.dead = True
            self.mario.x_vel = 0
            self.state = c.FROZEN
            self.game_info[c.MARIO_DEAD] = True

        if self.mario.dead:
            self.play_death_song()

    def play_death_song(self):
        if self.death_timer == 0:
            self.death_timer = self.current_time
        elif (self.current_time - self.death_timer) > 3000:
            self.set_game_info_values()
            self.done = True

    def set_game_info_values(self):
        if self.game_info[c.SCORE] > self.persist[c.TOP_SCORE]:
            self.persist[c.TOP_SCORE] = self.game_info[c.SCORE]
        if self.mario.dead:
            self.persist[c.LIVES] -= 1

        if self.persist[c.LIVES] == 0:
            self.next = c.GAME_OVER
            self.game_info[c.CAMERA_START_X] = 0
        elif not self.mario.dead:
            self.next = c.MAIN_MENU
            self.game_info[c.CAMERA_START_X] = 0
        elif self.overhead_info_display.time == 0:
            self.next = c.TIME_OUT
        else:
            self.next = c.LOAD_SCREEN

    def check_if_time_out(self):
        if self.overhead_info_display.time <= 0 and not self.mario.dead:
            self.state = c.FROZEN
            self.mario.start_death_jump(self.game_info)

    def update_viewport(self):
        """更新相机视图"""
        third = self.viewport.x + self.viewport.w//3
        mario_center = self.mario.rect.centerx
    
        if self.mario.x_vel > 0 and mario_center >= third:
            mult = 0.5 if self.mario.rect.right < self.viewport.centerx else 1
            new = self.viewport.x + mult * self.mario.x_vel
            highest = self.level_rect.w - self.viewport.w
            self.viewport.x = min(highest, new)
        elif self.mario.x_vel < 0 and mario_center <= third:
            mult = 0.5 if self.mario.rect.left > self.viewport.centerx else 1
            new = self.viewport.x + mult * self.mario.x_vel
            self.viewport.x = max(0, new)

    def blit_everything(self, surface):
        """绘制所有内容"""
        surface.fill((92, 148, 252))
        self.level.fill((92, 148, 252))
        self.level.blit(self.background, (0, 0))

        # 绘制地形和精灵
        self.random_terrain_group.draw(self.level)
        self.fixed_terrain_group.draw(self.level)  # 绘制固定砖块
        self.mario_and_enemy_group.draw(self.level)
        self.sprites_about_to_die_group.draw(self.level)  # 新增绘制即将死亡的精灵

        scaled = pg.transform.scale(self.level, surface.get_size())
        surface.blit(scaled, (0, 0))

        self.overhead_info_display.draw(surface)

    def check_if_mario_in_transition_state(self):
        if self.mario.in_transition_state:
            self.game_info[c.LEVEL_STATE] = self.state = c.FROZEN
        elif not self.mario.in_transition_state and self.state == c.FROZEN:
            self.game_info[c.LEVEL_STATE] = self.state = c.NOT_FROZEN

    def adjust_mario_for_y_ground_pipe_collisions(self, collider):
        """Mario与地面碰撞的y轴处理"""
        if collider.rect.bottom > self.mario.rect.bottom:
            self.mario.y_vel = 0
            self.mario.rect.bottom = collider.rect.top
            if self.mario.state == c.END_OF_LEVEL_FALL:
                self.mario.state = c.WALKING_TO_CASTLE
            else:
                self.mario.state = c.WALK
        elif collider.rect.top < self.mario.rect.top:
            self.mario.y_vel = 7
            self.mario.rect.top = collider.rect.bottom
            self.mario.state = c.FALL

    def adjust_mario_for_y_terrain_collisions(self, terrain):
        """Mario与随机地形碰撞的y轴处理"""
        if self.mario.rect.y > terrain.rect.y:
            # 从上方碰撞
            self.mario.y_vel = 7
            self.mario.rect.y = terrain.rect.bottom
            self.mario.state = c.FALL
        else:
            # 从下方碰撞
            self.mario.y_vel = 0
            self.mario.rect.bottom = terrain.rect.top
            self.mario.state = c.WALK

    def adjust_mario_for_y_enemy_collisions(self, enemy):
        """Mario与敌人y轴碰撞处理"""
        # 检查敌人是否已经死亡或处于死亡状态
        if enemy.state in (c.JUMPED_ON, c.DEATH_JUMP):
            return
        
        if self.mario.y_vel > 0:  # Mario正在下落（踩到敌人）
            setup.SFX['stomp'].play()
            self.game_info[c.SCORE] += 100
            self.moving_score_list.append(
                score.Score(enemy.rect.centerx - self.viewport.x,
                        enemy.rect.y, 100))
        
            # 处理敌人被踩后的状态
            enemy.state = c.JUMPED_ON
            enemy.death_timer = self.current_time
        
            # 如果是Goomba，从敌人组中移除
            if enemy.name == 'goomba':
                self.enemy_group.remove(enemy)
                self.mario_and_enemy_group.remove(enemy)
                self.sprites_about_to_die_group.add(enemy)
            # 如果是Koopa，直接移除（不要龟壳）
            elif enemy.name == 'koopa':
                self.enemy_group.remove(enemy)
                self.mario_and_enemy_group.remove(enemy) 
                self.sprites_about_to_die_group.add(enemy)
        
        # Mario弹跳
        self.mario.rect.bottom = enemy.rect.top
        self.mario.state = c.JUMP
        self.mario.y_vel = -7
        
        # Mario踩敌计数（用于Boss奖励）
        if hasattr(self.boss, 'mario_stomp_count'):
            self.boss.mario_stomp_count += 1

    def adjust_mario_for_x_enemy_collisions(self, enemy):
        """Mario与敌人x轴碰撞处理"""
        # 如果Mario处于无敌状态（包括作弊模式）
        if self.mario.invincible or (hasattr(self.mario, 'cheat_mode') and self.mario.cheat_mode):
            setup.SFX['kick'].play()
            self.game_info[c.SCORE] += 100
            self.moving_score_list.append(
                score.Score(self.mario.rect.right - self.viewport.x,
                            self.mario.rect.y, 100))
            
            # 敌人被踢飞
            enemy.kill()
            if hasattr(enemy, 'start_death_jump'):
                enemy.start_death_jump(c.RIGHT)
            self.sprites_about_to_die_group.add(enemy)
        
        # 如果Mario是大形态但不是无敌状态
        elif self.mario.big and not self.mario.invincible:
            setup.SFX['pipe'].play()
            self.mario.fire = False
            self.mario.y_vel = -1
            self.mario.state = c.BIG_TO_SMALL
        
        # 如果Mario处于受伤无敌状态
        elif self.mario.hurt_invincible:
            pass
        
        # 普通小Mario碰到敌人
        else:
            self.mario.start_death_jump(self.game_info)
            self.state = c.FROZEN
