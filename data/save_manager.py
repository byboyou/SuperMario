import os
import pickle
import pygame as pg
from . import constants as c

class SaveManager:
    def __init__(self, save_dir="saves"):
        self.save_dir = save_dir
        self.current_slot = 1
        self.max_slots = 3
        self.create_save_directory()
    
    def create_save_directory(self):
        """创建存档目录"""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
    
    def get_save_path(self, slot=None):
        """获取存档文件路径"""
        if slot is None:
            slot = self.current_slot
        return os.path.join(self.save_dir, f"save_{slot}.dat")
    
    def save_game(self, game_info, level_state, mario_state, slot=None):
        """保存游戏"""
        try:
            if slot is None:
                slot = self.current_slot
            
            save_data = {
                'game_info': game_info.copy(),
                'level_state': level_state,
                'mario_state': mario_state,
                'timestamp': pg.time.get_ticks()
            }
            
            # 确保游戏信息中的关键数据被保存
            save_data['game_info'][c.CURRENT_TIME] = pg.time.get_ticks()
            
            with open(self.get_save_path(slot), 'wb') as f:
                pickle.dump(save_data, f)
            
            print(f"游戏已保存到槽位 {slot}")
            return True
        except Exception as e:
            print(f"保存游戏失败: {e}")
            return False
    
    def load_game(self, slot=None):
        """加载游戏"""
        try:
            if slot is None:
                slot = self.current_slot
            
            save_path = self.get_save_path(slot)
            if not os.path.exists(save_path):
                print(f"槽位 {slot} 没有存档")
                return None
            
            with open(save_path, 'rb') as f:
                save_data = pickle.load(f)
            
            print(f"从槽位 {slot} 加载游戏成功")
            return save_data
        except Exception as e:
            print(f"加载游戏失败: {e}")
            return None
    
    def slot_exists(self, slot):
        """检查存档槽位是否存在"""
        return os.path.exists(self.get_save_path(slot))
    
    def get_slot_info(self, slot):
        """获取存档槽位信息"""
        save_data = self.load_game(slot)
        if save_data:
            return {
                'exists': True,
                'score': save_data['game_info'].get(c.SCORE, 0),
                'lives': save_data['game_info'].get(c.LIVES, 3),
                'coins': save_data['game_info'].get(c.COIN_TOTAL, 0),
                'timestamp': save_data.get('timestamp', 0)
            }
        return {'exists': False}
    
    def delete_save(self, slot):
        """删除存档"""
        try:
            save_path = self.get_save_path(slot)
            if os.path.exists(save_path):
                os.remove(save_path)
                print(f"槽位 {slot} 的存档已删除")
                return True
        except Exception as e:
            print(f"删除存档失败: {e}")
        return False