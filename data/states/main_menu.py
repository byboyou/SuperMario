__author__ = 'justinarmstrong'

import pygame as pg
from .. import setup, tools
from .. import constants as c
from .. components import info, mario


class Menu(tools._State):
    def __init__(self):
        """Initializes the state"""
        tools._State.__init__(self)
        persist = {c.COIN_TOTAL: 0,
                   c.SCORE: 0,
                   c.LIVES: 3,
                   c.TOP_SCORE: 0,
                   c.CURRENT_TIME: 0.0,
                   c.LEVEL_STATE: None,
                   c.CAMERA_START_X: 0,
                   c.MARIO_DEAD: False}
        self.startup(0.0, persist)
        self.last_key_press_time = 0
        self.key_pressed_i = False  # 防止I键连续触发
        self.key_pressed_esc = False  # 防止ESC键连续触发

    def startup(self, current_time, persist):
        """Called every time the game's state becomes this one.  Initializes
        certain values"""
        self.next = c.LOAD_SCREEN
        self.persist = persist
        self.game_info = persist
        self.overhead_info = info.OverheadInfo(self.game_info, c.MAIN_MENU)

        self.sprite_sheet = setup.GFX['title_screen']
        self.setup_background()
        self.setup_mario()
        self.setup_cursor()
        self.setup_instructions()  # 新增：设置说明界面
        self.setup_fonts()  # 新增：设置字体

    def setup_fonts(self):
        """设置字体"""
        # 尝试从文件加载中文字体
        try:
            # 假设字体文件在项目根目录的 fonts 文件夹中
            self.chinese_font = pg.font.Font('C:/Windows/Fonts/simhei.ttf', 24)
            print("成功从文件加载中文字体")
        except:
            # 如果文件加载失败，尝试系统字体
            chinese_font_names = ['SimHei', 'Microsoft YaHei', 'KaiTi', 'SimSun']
            self.chinese_font = None
            
            for font_name in chinese_font_names:
                try:
                    self.chinese_font = pg.font.SysFont(font_name, 24)
                    print(f"成功加载系统字体: {font_name}")
                    break
                except:
                    continue
            
            # 如果都失败，使用默认字体
            if self.chinese_font is None:
                print("无法加载中文字体，使用默认字体")
                self.chinese_font = pg.font.Font(None, 24)
        
        # 英文字体
        self.menu_font = pg.font.SysFont('arial', 24)

    def setup_instructions(self):
        """设置游戏说明界面"""
        self.showing_instructions = False
        
        # 创建说明界面
        self.instructions_surface = pg.Surface((450, 450))
        self.instructions_surface.fill((0, 0, 0))
        
        # 添加白色边框
        border_rect = pg.Rect(0, 0, 450, 450)
        pg.draw.rect(self.instructions_surface, (255, 255, 255), border_rect, 4)


    def setup_cursor(self):
        """Creates the mushroom cursor to select 1 or 2 player game"""
        self.cursor = pg.sprite.Sprite()
        dest = (220, 358)
        self.cursor.image, self.cursor.rect = self.get_image(
            24, 160, 8, 8, dest, setup.GFX['item_objects'])
        self.cursor.state = c.PLAYER1


    def setup_mario(self):
        """Places Mario at the beginning of the level"""
        self.mario = mario.Mario()
        self.mario.rect.x = 110
        self.mario.rect.bottom = c.GROUND_HEIGHT


    def setup_background(self):
        """Setup the background image to blit"""
        self.background = setup.GFX['level_1']
        self.background_rect = self.background.get_rect()
        self.background = pg.transform.scale(self.background,
                                   (int(self.background_rect.width*c.BACKGROUND_MULTIPLER),
                                    int(self.background_rect.height*c.BACKGROUND_MULTIPLER)))
        self.viewport = setup.SCREEN.get_rect(bottom=setup.SCREEN_RECT.bottom)

        self.image_dict = {}
        self.image_dict['GAME_NAME_BOX'] = self.get_image(
            1, 60, 176, 88, (170, 100), setup.GFX['title_screen'])



    def get_image(self, x, y, width, height, dest, sprite_sheet):
        """Returns images and rects to blit onto the screen"""
        image = pg.Surface([width, height])
        rect = image.get_rect()

        image.blit(sprite_sheet, (0, 0), (x, y, width, height))
        if sprite_sheet == setup.GFX['title_screen']:
            image.set_colorkey((255, 0, 220))
            image = pg.transform.scale(image,
                                   (int(rect.width*c.SIZE_MULTIPLIER),
                                    int(rect.height*c.SIZE_MULTIPLIER)))
        else:
            image.set_colorkey(c.BLACK)
            image = pg.transform.scale(image,
                                   (int(rect.width*3),
                                    int(rect.height*3)))

        rect = image.get_rect()
        rect.x = dest[0]
        rect.y = dest[1]
        return (image, rect)


    def update(self, surface, keys, current_time):
        """Updates the state every refresh"""
        self.current_time = current_time
        self.game_info[c.CURRENT_TIME] = self.current_time
        
        # 检测I键按下
        if keys[pg.K_i]:
            if not self.key_pressed_i:
                self.showing_instructions = not self.showing_instructions
                self.key_pressed_i = True
        else:
            self.key_pressed_i = False

        # 检测ESC键按下（用于退出说明界面）
        if keys[pg.K_ESCAPE]:
            if not self.key_pressed_esc:
                if self.showing_instructions:
                    self.showing_instructions = False
                self.key_pressed_esc = True
        else:
            self.key_pressed_esc = False
        
        # 根据是否显示说明界面来更新不同的内容
        if not self.showing_instructions:
            self.update_cursor(keys)
        
        # 始终更新游戏信息
        self.overhead_info.update(self.game_info)

        # 先绘制背景
        surface.blit(self.background, self.viewport, self.viewport)
        surface.blit(self.image_dict['GAME_NAME_BOX'][0],
                    self.image_dict['GAME_NAME_BOX'][1])
        
        if not self.showing_instructions:
            # 正常显示主菜单
            surface.blit(self.mario.image, self.mario.rect)
            surface.blit(self.cursor.image, self.cursor.rect)

        else:
            # 显示说明界面
            # 先绘制半透明黑色背景
            overlay = pg.Surface(surface.get_size())
            overlay.fill((0, 0, 0))
            overlay.set_alpha(200)
            surface.blit(overlay, (0, 0))
            
            # 绘制说明窗口
            self.draw_instructions()
            instructions_rect = self.instructions_surface.get_rect(center=surface.get_rect().center)
            surface.blit(self.instructions_surface, instructions_rect)

        # 只在主菜单模式下显示顶部游戏信息
        if not self.showing_instructions:
            self.overhead_info.draw(surface)


    def update_cursor(self, keys):
        """Update the position of the cursor"""
        input_list = [pg.K_RETURN, pg.K_a, pg.K_s]

        if self.cursor.state == c.PLAYER1:
            self.cursor.rect.y = 358
            if keys[pg.K_DOWN]:
                self.cursor.state = c.PLAYER2
            for input in input_list:
                if keys[input]:
                    self.reset_game_info()
                    self.done = True
        elif self.cursor.state == c.PLAYER2:
            self.cursor.rect.y = 403
            if keys[pg.K_UP]:
                self.cursor.state = c.PLAYER1


    def reset_game_info(self):
        """Resets the game info in case of a Game Over and restart"""
        self.game_info[c.COIN_TOTAL] = 0
        self.game_info[c.SCORE] = 0
        self.game_info[c.LIVES] = 3
        self.game_info[c.CURRENT_TIME] = 0.0
        self.game_info[c.LEVEL_STATE] = None

        self.persist = self.game_info


    def draw_instructions(self):
        """绘制说明界面"""
        # 清空说明界面，重新填充黑色背景
        self.instructions_surface.fill((0, 0, 0))
        border_rect = pg.Rect(0, 0, 450, 450)
        pg.draw.rect(self.instructions_surface, (255, 255, 255), border_rect, 4)

        # 绘制说明文本
        instructions = [
            "CONTROLS:",
            "A/D: 左右移动",
            "SPACE: 跳跃",
            "W: 冲刺/火球",
            "S: 蹲下",
            "",
            "OBJECTIVES:",
            "- 到达旗帜处",
            "- 收集金币和蘑菇",
            "- 击杀敌人",
            "",
            "Press ESC to return"
        ]
        
        # 绘制标题
        title = self.menu_font.render("GAME INSTRUCTIONS", True, (255, 255, 0))
        title_rect = title.get_rect(centerx=self.instructions_surface.get_width()//2)
        self.instructions_surface.blit(title, (title_rect.x, 20))
        
        # 绘制说明文本
        for i, line in enumerate(instructions):
            if line == "CONTROLS:" or line == "OBJECTIVES:":
                text = self.chinese_font.render(line, True, (255, 215, 0))  # 金色
            elif line.startswith("-"):
                text = self.chinese_font.render(line, True, (144, 238, 144))  # 浅绿色
            else:
                text = self.chinese_font.render(line, True, (255, 255, 255))
            
            text_rect = text.get_rect(centerx=self.instructions_surface.get_width()//2)
            self.instructions_surface.blit(text, (text_rect.x, 60 + i * 30))
















