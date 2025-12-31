from __future__ import division

import os
import pickle

import pygame as pg
from .. import setup, tools
from .. import constants as c
from .. import game_sound
from .. components import mario
from .. components import collider
from .. components import bricks
from .. components import coin_box
from .. components import enemies
from .. components import checkpoint
from .. components import flagpole
from .. components import info
from .. components import score
from .. components import castle_flag


class Level2(tools._State):
    def __init__(self):
        tools._State.__init__(self)

    def startup(self, current_time, persist):
        """Called when the State object is created"""
        self.game_info = persist
        self.persist = self.game_info
        self.game_info[c.CURRENT_TIME] = current_time
        self.game_info[c.LEVEL_STATE] = c.NOT_FROZEN
        self.game_info[c.MARIO_DEAD] = False

        self.state = c.NOT_FROZEN
        self.death_timer = 0

        self.moving_score_list = []
        self.overhead_info_display = info.OverheadInfo(self.game_info, c.LEVEL)
        self.sound_manager = game_sound.Sound(self.overhead_info_display)

        self.setup_background()
        self.setup_ground()
        self.setup_mario()
        self.setup_spritegroups()

    def setup_background(self):
        """Sets the background image, rect and scales it to the correct proportions"""
        self.background = setup.GFX['level_2']
        self.back_rect = self.background.get_rect()
        
        # 获取屏幕尺寸
        screen_info = pg.display.Info()
        screen_width = screen_info.current_w
        screen_height = screen_info.current_h
        
        # 计算适合屏幕的尺寸（留出空间给状态栏）
        target_height = screen_height - 100  # 留出100像素给状态栏
        target_width = int(target_height * 1.5)  # 保持1.5:1的宽高比（300x200是1.5:1）
        
        # 如果宽度超过屏幕宽度，则按宽度缩放
        if target_width > screen_width:
            target_width = screen_width
            target_height = int(target_width * 2/3)  # 300x200是1.5:1，所以高=宽*2/3
        
        # 缩放背景
        self.background = pg.transform.scale(self.background, (target_width, target_height))
        self.back_rect = self.background.get_rect()
        
        width = self.back_rect.width
        height = self.back_rect.height

        self.level = pg.Surface((width, height)).convert()
        self.level_rect = self.level.get_rect()
        self.viewport = setup.SCREEN.get_rect(bottom=self.level_rect.bottom)
        self.viewport.x = self.game_info[c.CAMERA_START_X]
        
        # 更新地面尺寸
        self.level_width = width
        self.level_height = height

    def setup_ground(self):
        """Creates collideable, invisible rectangles over top of the ground for sprites to walk on"""
        # Level2地面为图片下方24像素高部分
        ground_y = self.level_height - 60  # 底部24像素是地面
        ground_rect = collider.Collider(0, ground_y, self.level_width, 60)
        self.ground_group = pg.sprite.Group(ground_rect)

    def setup_mario(self):
        """Places Mario at the beginning of the level"""
        self.mario = mario.Mario()
        self.mario.rect.x = 50  # 起始位置
        self.mario.rect.bottom = self.level_height - 60 # 地面高度

    def setup_spritegroups(self):
        """Sprite groups created for convenience"""
        self.ground_step_pipe_group = pg.sprite.Group(self.ground_group)
        self.mario_and_enemy_group = pg.sprite.Group(self.mario)

    def update(self, surface, keys, current_time):
        """Updates Entire level using states. Called by the control object"""
        self.game_info[c.CURRENT_TIME] = self.current_time = current_time
        
        self.handle_states(keys)
        self.check_if_time_out()
        self.blit_everything(surface)
        self.sound_manager.update(self.game_info, self.mario)

    def handle_states(self, keys):
        """If the level is in a FROZEN state, only mario will update"""
        if self.state == c.FROZEN:
            self.update_during_transition_state(keys)
        elif self.state == c.NOT_FROZEN:
            self.update_all_sprites(keys)

    def update_during_transition_state(self, keys):
        """Updates mario in a transition state"""
        self.mario.update(keys, self.game_info, pg.sprite.Group())  # 空powerup_group
        for score in self.moving_score_list:
            score.update(self.moving_score_list, self.game_info)
        self.check_if_mario_in_transition_state()
        self.check_for_mario_death()
        self.overhead_info_display.update(self.game_info, self.mario)

    def check_if_mario_in_transition_state(self):
        """If mario is in a transition state, the level will be in a FREEZE state"""
        if self.mario.in_transition_state:
            self.game_info[c.LEVEL_STATE] = self.state = c.FROZEN
        elif self.mario.in_transition_state == False:
            if self.state == c.FROZEN:
                self.game_info[c.LEVEL_STATE] = self.state = c.NOT_FROZEN

    def update_all_sprites(self, keys):
        """Updates the location of all sprites on the screen."""
        self.mario.update(keys, self.game_info, pg.sprite.Group())  # 空powerup_group
        for score in self.moving_score_list:
            score.update(self.moving_score_list, self.game_info)
        
        self.adjust_sprite_positions()
        self.check_if_mario_in_transition_state()
        self.check_for_mario_death()
        self.update_viewport()
        self.overhead_info_display.update(self.game_info, self.mario)

    def adjust_sprite_positions(self):
        """Adjusts sprites by their x and y velocities and collisions"""
        self.adjust_mario_position()

    def adjust_mario_position(self):
        """Adjusts Mario's position based on his x, y velocities and potential collisions"""
        self.last_x_position = self.mario.rect.right
        self.mario.rect.x += round(self.mario.x_vel)
        self.check_mario_x_collisions()

        if self.mario.in_transition_state == False:
            self.mario.rect.y += round(self.mario.y_vel)
            self.check_mario_y_collisions()

        # 边界检查 - Level2地图较小，限制移动范围
        if self.mario.rect.x < 0:
            self.mario.rect.x = 0
        elif self.mario.rect.right > self.level_width:  # 使用动态的地图宽度
            self.mario.rect.right = self.level_width

    def check_mario_x_collisions(self):
        """Check for collisions after Mario is moved on the x axis"""
        collider = pg.sprite.spritecollideany(self.mario, self.ground_step_pipe_group)
        
        if collider:
            self.adjust_mario_for_x_collisions(collider)

    def adjust_mario_for_x_collisions(self, collider):
        """Puts Mario flush next to the collider after moving on the x axis"""
        if self.mario.rect.x < collider.rect.x:
            self.mario.rect.right = collider.rect.left
        else:
            self.mario.rect.left = collider.rect.right

        self.mario.x_vel = 0

    def check_mario_y_collisions(self):
        """Checks for collisions when Mario moves along the y-axis"""
        ground_step_or_pipe = pg.sprite.spritecollideany(self.mario, self.ground_step_pipe_group)

        if ground_step_or_pipe:
            self.adjust_mario_for_y_ground_pipe_collisions(ground_step_or_pipe)

        self.test_if_mario_is_falling()

    def adjust_mario_for_y_ground_pipe_collisions(self, collider):
        """Mario collisions with pipes on the y-axis"""
        if collider.rect.bottom > self.mario.rect.bottom:
            self.mario.y_vel = 0
            self.mario.rect.bottom = collider.rect.top
            self.mario.state = c.WALK
        elif collider.rect.top < self.mario.rect.top:
            self.mario.y_vel = 7
            self.mario.rect.top = collider.rect.bottom
            self.mario.state = c.FALL

    def test_if_mario_is_falling(self):
        """Changes Mario to a FALL state if more than a pixel above a pipe, ground, step or box"""
        self.mario.rect.y += 1
        test_collide_group = pg.sprite.Group(self.ground_step_pipe_group)

        if pg.sprite.spritecollideany(self.mario, test_collide_group) is None:
            if self.mario.state != c.JUMP and self.mario.state != c.DEATH_JUMP:
                self.mario.state = c.FALL

        self.mario.rect.y -= 1

    def check_for_mario_death(self):
        """Restarts the level if Mario is dead"""
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
        """sets the new game values after a player's death"""
        if self.game_info[c.SCORE] > self.persist[c.TOP_SCORE]:
            self.persist[c.TOP_SCORE] = self.game_info[c.SCORE]
        if self.mario.dead:
            self.persist[c.LIVES] -= 1

        if self.persist[c.LIVES] == 0:
            self.next = c.GAME_OVER
            self.game_info[c.CAMERA_START_X] = 0
        elif self.mario.dead == False:
            self.next = c.MAIN_MENU
            self.game_info[c.CAMERA_START_X] = 0
        elif self.overhead_info_display.time == 0:
            self.next = c.TIME_OUT
        else:
            self.next = c.LOAD_SCREEN

    def check_if_time_out(self):
        """Check if time has run down to 0"""
        if self.overhead_info_display.time <= 0 and not self.mario.dead:
            self.state = c.FROZEN
            self.mario.start_death_jump(self.game_info)

    def update_viewport(self):
        """Level2地图较小，不需要复杂的视角移动逻辑"""
        # 由于Level2地图固定为300x200，而屏幕为800x600，可以居中显示或简单处理
        pass

    def blit_everything(self, surface):
        """Blit all sprites to the main surface"""
        # 清空整个屏幕
        surface.fill((92, 148, 252))  # 马里奥风格的天空蓝色背景
        
        # 计算缩放比例以适应屏幕
        screen_width, screen_height = surface.get_size()
        level_width, level_height = 300, 200
        
        # 计算适合屏幕的缩放比例
        scale_x = screen_width / level_width
        scale_y = screen_height / level_height
        scale = min(scale_x, scale_y)  # 使用较小的缩放比例以保持宽高比
        
        # 计算缩放后的尺寸
        scaled_width = int(level_width * scale)
        scaled_height = int(level_height * scale)
        
        # 计算居中位置
        level_x = (screen_width - scaled_width) // 2
        level_y = (screen_height - scaled_height) // 2
        
        # 清空level surface
        self.level.fill((92, 148, 252))  # 马里奥风格的天空蓝色
        
        # 绘制背景
        self.level.blit(self.background, (0, 0))
        
        # 绘制马里奥
        self.mario_and_enemy_group.draw(self.level)
        
        # 缩放level surface
        scaled_level = pg.transform.scale(self.level, (scaled_width, scaled_height))
        
        # 将缩放后的level surface绘制到屏幕上
        surface.blit(scaled_level, (level_x, level_y))
        
        # 绘制游戏信息
        self.overhead_info_display.draw(surface)