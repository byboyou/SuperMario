__author__ = 'justinarmstrong'

import os
import pygame as pg
from . import constants as c

keybinding = {
    'action':pg.K_w,
    'jump':pg.K_SPACE,
    'left':pg.K_a,
    'right':pg.K_d,
    'down':pg.K_s
}

class Control(object):
    """Control class for entire project. Contains the game loop, and contains
    the event_loop which passes events to States as needed. Logic for flipping
    states is also found here."""
    def __init__(self, caption):
        self.screen = pg.display.get_surface()
        self.done = False
        self.clock = pg.time.Clock()
        self.caption = caption
        self.fps = 60
        self.show_fps = False
        self.current_time = 0.0
        self.keys = pg.key.get_pressed()
        self.state_dict = {}
        self.state_name = None
        self.state = None
        # 存档相关属性
        self.save_manager = None
        self.show_save_menu = False
        self.save_menu_cursor = 1
        self.save_menu_mode = 'save'

    def setup_states(self, state_dict, start_state):
        self.state_dict = state_dict
        self.state_name = start_state
        self.state = self.state_dict[self.state_name]
        # 初始化存档管理器
        from .save_manager import SaveManager
        self.save_manager = SaveManager()

    def event_loop(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.done = True
            elif event.type == pg.KEYDOWN:
                self.keys = pg.key.get_pressed()
                self.toggle_show_fps(event.key)
                
                # 检测 F 键作弊
                if event.key == pg.K_f:
                    self.toggle_cheat_mode()
                
                # 新增存档读档按键
                elif event.key == pg.K_F5:
                    self.quick_save()
                elif event.key == pg.K_F9:
                    self.quick_load()
                elif event.key == pg.K_F6:
                    self.toggle_save_menu('save')
                elif event.key == pg.K_F7:
                    self.toggle_save_menu('load')
                
                # 存档菜单导航
                elif self.show_save_menu:
                    if event.key == pg.K_UP:
                        self.save_menu_cursor = max(1, self.save_menu_cursor - 1)
                    elif event.key == pg.K_DOWN:
                        self.save_menu_cursor = min(3, self.save_menu_cursor + 1)
                    elif event.key == pg.K_RETURN:
                        self.handle_save_menu_selection()
                    elif event.key == pg.K_ESCAPE:
                        self.show_save_menu = False
                    elif event.key == pg.K_d and self.save_menu_mode == 'load':
                        # 删除存档（仅限加载模式）
                        self.save_manager.delete_save(self.save_menu_cursor)
                        
            elif event.type == pg.KEYUP:
                self.keys = pg.key.get_pressed()
            self.state.get_event(event)

    def toggle_save_menu(self, mode='save'):
        """切换存档菜单显示"""
        # 只在Level1状态下显示存档菜单
        if self.state_name == c.LEVEL1:
            self.show_save_menu = not self.show_save_menu
            if self.show_save_menu:
                self.save_menu_cursor = 1
                self.save_menu_mode = mode

    def handle_save_menu_selection(self):
        """处理存档菜单选择"""
        if self.show_save_menu and self.state_name == c.LEVEL1:
            if self.save_menu_mode == 'save':
                # 保存模式
                if hasattr(self.state, 'get_save_data'):
                    save_data = self.state.get_save_data()
                    if save_data:
                        success = self.save_manager.save_game(
                            save_data['game_info'],
                            save_data['level_state'],
                            save_data['mario_state'],
                            self.save_menu_cursor
                        )
                        if success:
                            self.show_quick_message(f"存档成功! 槽位 {self.save_menu_cursor}")
            else:
                # 加载模式
                save_data = self.save_manager.load_game(self.save_menu_cursor)
                if save_data and hasattr(self.state, 'load_from_save_data'):
                    success = self.state.load_from_save_data(save_data)
                    if success:
                        self.show_quick_message(f"读档成功! 槽位 {self.save_menu_cursor}")
            
            self.show_save_menu = False

    def quick_save(self):
        """快速存档到当前槽位"""
        if self.state_name == c.LEVEL1 and hasattr(self.state, 'get_save_data'):
            save_data = self.state.get_save_data()
            if save_data:
                success = self.save_manager.save_game(
                    save_data['game_info'],
                    save_data['level_state'],
                    save_data['mario_state']
                )
                if success:
                    self.show_quick_message("快速存档成功!")

    def quick_load(self):
        """快速从当前槽位加载"""
        if self.state_name == c.LEVEL1:
            save_data = self.save_manager.load_game()
            if save_data and hasattr(self.state, 'load_from_save_data'):
                success = self.state.load_from_save_data(save_data)
                if success:
                    self.show_quick_message("快速读档成功!")

    def show_quick_message(self, message):
        """显示快速操作提示"""
        self.quick_message = message
        self.quick_message_timer = self.current_time

    def update(self):
        self.current_time = pg.time.get_ticks()
        if self.state.quit:
            self.done = True
        elif self.state.done:
            self.flip_state()
        self.state.update(self.screen, self.keys, self.current_time)

        # 更新存档菜单显示
        if self.show_save_menu:
            self.draw_save_menu()
        
        # 显示快速操作提示
        if hasattr(self, 'quick_message_timer'):
            if self.current_time - self.quick_message_timer < 2000:  # 显示2秒
                self.draw_quick_message()

    def draw_save_menu(self):
        """绘制存档菜单"""
        # 只在Level1状态下显示存档菜单
        if self.state_name != c.LEVEL1:
            self.show_save_menu = False
            return
        
        # 创建半透明背景
        overlay = pg.Surface(self.screen.get_size())
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # 绘制存档菜单
        menu_width, menu_height = 400, 300
        menu_x = (self.screen.get_width() - menu_width) // 2
        menu_y = (self.screen.get_height() - menu_height) // 2
        
        # 菜单背景
        menu_bg = pg.Surface((menu_width, menu_height))
        menu_bg.fill((50, 50, 50))
        menu_border = pg.Rect(0, 0, menu_width, menu_height)
        pg.draw.rect(menu_bg, (255, 255, 255), menu_border, 3)
        self.screen.blit(menu_bg, (menu_x, menu_y))
        
        # 标题
        font = pg.font.SysFont('Arial', 32)
        title_text = "存档管理" if self.save_menu_mode == 'save' else "读取存档"
        title = font.render(title_text, True, (255, 255, 255))
        self.screen.blit(title, (menu_x + (menu_width - title.get_width()) // 2, menu_y + 20))
        
        # 存档槽位信息
        slot_font = pg.font.SysFont('Arial', 24)
        for i in range(1, 4):
            slot_info = self.save_manager.get_slot_info(i)
            y_pos = menu_y + 80 + (i-1)*60
            
            # 高亮当前选中的槽位
            if i == self.save_menu_cursor:
                pg.draw.rect(self.screen, (100, 100, 100), 
                           (menu_x + 50, y_pos - 5, menu_width - 100, 40))
            
            if slot_info['exists']:
                text = f"槽位 {i}: 分数 {slot_info['score']} | 生命 {slot_info['lives']} | 金币 {slot_info['coins']}"
                color = (255, 255, 255)
            else:
                text = f"槽位 {i}: 空"
                color = (150, 150, 150)
            
            slot_text = slot_font.render(text, True, color)
            self.screen.blit(slot_text, (menu_x + 60, y_pos))
        
        # 操作提示
        hint_font = pg.font.SysFont('Arial', 18)
        hints = [
            "↑↓: 选择槽位  Enter: 确认  ESC: 退出",
            "F5: 快速存档  F9: 快速读档"
        ]
        
        if self.save_menu_mode == 'load':
            hints.append("D: 删除选中存档")
        
        for i, hint in enumerate(hints):
            hint_text = hint_font.render(hint, True, (200, 200, 200))
            self.screen.blit(hint_text, (menu_x + (menu_width - hint_text.get_width()) // 2, 
                                       menu_y + menu_height - 60 + i*25))

    def draw_quick_message(self):
        """绘制快速操作提示"""
        font = pg.font.SysFont('Arial', 24)
        text = font.render(self.quick_message, True, (255, 255, 0))
        text_rect = text.get_rect(center=(self.screen.get_width() // 2, 100))
        
        # 添加背景
        bg_rect = text_rect.inflate(20, 10)
        bg_surface = pg.Surface((bg_rect.width, bg_rect.height))
        bg_surface.set_alpha(200)
        bg_surface.fill((0, 0, 0))
        self.screen.blit(bg_surface, bg_rect)
        
        # 绘制文字
        self.screen.blit(text, text_rect)

    def flip_state(self):
        previous, self.state_name = self.state_name, self.state.next
        persist = self.state.cleanup()
        self.state = self.state_dict[self.state_name]
        self.state.startup(self.current_time, persist)
        self.state.previous = previous


    def event_loop(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.done = True
            elif event.type == pg.KEYDOWN:
                self.keys = pg.key.get_pressed()
                # 检测 F 键作弊
                self.toggle_show_fps(event.key)
                if event.key == pg.K_f:
                    self.toggle_cheat_mode()
            elif event.type == pg.KEYUP:
                self.keys = pg.key.get_pressed()
            self.state.get_event(event)
    def toggle_cheat_mode(self):
        """切换作弊模式"""
        # 如果当前状态是Level1，则调用其作弊方法
        if hasattr(self.state, 'toggle_cheat_mode'):
            self.state.toggle_cheat_mode(pg.time.get_ticks())


    def toggle_show_fps(self, key):
        if key == pg.K_F5:
            self.show_fps = not self.show_fps
            if not self.show_fps:
                pg.display.set_caption(self.caption)


    def main(self):
        """Main loop for entire program"""
        while not self.done:
            self.event_loop()
            self.update()
            pg.display.update()
            self.clock.tick(self.fps)
            if self.show_fps:
                fps = self.clock.get_fps()
                with_fps = "{} - {:.2f} FPS".format(self.caption, fps)
                pg.display.set_caption(with_fps)


class _State(object):
    def __init__(self):
        self.start_time = 0.0
        self.current_time = 0.0
        self.done = False
        self.quit = False
        self.next = None
        self.previous = None
        self.persist = {}

    def get_event(self, event):
        pass

    def startup(self, current_time, persistant):
        self.persist = persistant
        self.start_time = current_time

    def cleanup(self):
        self.done = False
        return self.persist

    def update(self, surface, keys, current_time):
        pass



def load_all_gfx(directory, colorkey=(255,0,255), accept=('.png', 'jpg', 'bmp')):
    graphics = {}
    for pic in os.listdir(directory):
        name, ext = os.path.splitext(pic)
        if ext.lower() in accept:
            img = pg.image.load(os.path.join(directory, pic))
            if img.get_alpha():
                img = img.convert_alpha()
            else:
                img = img.convert()
                img.set_colorkey(colorkey)
            graphics[name]=img
    return graphics


def load_all_music(directory, accept=('.wav', '.mp3', '.ogg', '.mdi')):
    songs = {}
    for song in os.listdir(directory):
        name,ext = os.path.splitext(song)
        if ext.lower() in accept:
            songs[name] = os.path.join(directory, song)
    return songs


def load_all_fonts(directory, accept=('.ttf')):
    return load_all_music(directory, accept)


def load_all_sfx(directory, accept=('.wav','.mpe','.ogg','.mdi')):
    effects = {}
    for fx in os.listdir(directory):
        name, ext = os.path.splitext(fx)
        if ext.lower() in accept:
            effects[name] = pg.mixer.Sound(os.path.join(directory, fx))
    return effects











