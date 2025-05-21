# -*- coding: utf-8 -*-
"""
# @项目名称 :pytorch
# @文件名称 :ImageLabel.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/5/14 15:01
# @文件介绍 :
"""
import os
import tkinter as tk
from math import ceil, sqrt
from re import fullmatch
from shutil import move
from subprocess import Popen
from threading import Thread
from time import sleep
from tkinter import messagebox

import numpy as np
import win32clipboard
from PIL import Image, ImageTk
from cv2 import resize, INTER_CUBIC, imdecode, IMREAD_COLOR
from easyocr import easyocr
from logger.logger import Logger


class ImageLabel:
    def __init__(self):
        self.images = []
        self.root = tk.Tk()
        self.folder_path: str = os.getcwd()
        self.flag = False
        self.reader = None
        self.control_set = {}
        self.logger = Logger(title="日志", log_dir="log/", is_color=True, categorize=True)

    @staticmethod
    def is_all_chinese(text):
        """判断字符串是否全为汉字"""
        return bool(fullmatch(r'[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df]', text))

    def discriminate_img(self):
        """
        对图片进行识别
        :return:
        """

        def imread_chinese(path):
            """
            解决cv2不支持中文路径
            :param path:
            :return:
            """
            with open(path, 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.uint8)
            return imdecode(data, IMREAD_COLOR)

        if self.reader:
            text_list = []
            for il in self.images:
                # 读取图像并进行 OCR
                result = self.reader.readtext(
                    resize(imread_chinese(il), None, fx=8, fy=8, interpolation=INTER_CUBIC),
                    paragraph=False, text_threshold=0.6, low_text=0.3, width_ths=0.1, height_ths=0.1, add_margin=0.15)
                if result:
                    text_list.append(result[0])
            self.control_set.get("font_label").config(text='')
            self.control_set.get("cond_label").config(text='', bg=None)
            if len(set([tl[1] for tl in text_list if self.is_all_chinese(tl[1])])) == 1:
                value = min([round(float(tl[2])) for tl in text_list])
                bg = "lightgreen" if value > 0.8 else "blue" if value > 0.5 else "yellow" if value > 0.3 else "red"
                self.control_set.get("font_label").config(text=text_list[0][1])
                self.control_set.get("cond_label").config(text=value, bg=bg)

    @staticmethod
    def on_entry_click(event, text):
        """当 Entry 被点击时，如果内容是提示文字，则清空"""
        if event.get() == text:
            event.config(fg="black")
            event.delete(0, "end")
        else:
            event.config(fg="gray")

    @staticmethod
    def on_focusout(event, text):
        """当 Entry 失去焦点时，如果为空，则恢复提示文字"""
        if event.get() == "":
            event.config(fg="gray")
            event.insert(0, text)
        else:
            event.config(fg="black")

    def input_tip(self, input_box, text):
        """
        输入框提示
        :param input_box:
        :param text:
        :return:
        """
        input_box.insert(0, text)
        input_box.config(fg="gray")
        input_box.bind("<FocusIn>", lambda event: self.on_entry_click(input_box, text))
        input_box.bind("<FocusOut>", lambda event: self.on_focusout(input_box, text))

    def ui_layout(self):
        self.root.title("数据分类助手V1.1.1")
        self.root.geometry("300x450")
        # 允许窗口缩放
        self.root.resizable(False, False)

        self.control_set.update({"top_content": self.create_pack_box(y=0, x=0, b=None)})
        self.input_box_path()
        self.data_statistics()
        self.show_ocr_info()
        self.check_box()
        self.input_box_font()
        self.control_set.update({"img_content": self.create_pack_box(h=290, y=160, x=0)})

    def data_statistics(self):
        """
        数据统计
        :return:
        """
        frame = self.label_frame(self.control_set.get("top_content"), 20, 0, "统计")

        label_total = tk.Label(frame, text='总计：', width=15)
        label_total.pack(padx=0, side=tk.LEFT)

        label_leave = tk.Label(frame, text='剩余：', width=15)
        label_leave.pack(pady=0, side=tk.LEFT)
        self.control_set.update({"label_total": label_total, "label_leave": label_leave})

    def create_pack_box(self, w=300, h=160, y=0, x=0, b: str | None = 'gray'):
        """
        创建容器框
        :return:
        """
        frame = tk.Frame(self.root, width=w, height=h, bg=b, borderwidth=2, relief="solid")
        frame.propagate(False)
        frame.place(y=y, x=x)
        return frame

    def input_box_path(self):
        """
        输入框
        :return:
        """
        frame = self.label_frame(self.control_set.get("top_content"), 0, 0, "路径")
        path_entry = tk.Entry(frame, width=30)
        self.input_tip(path_entry, '请输入图片所在文件夹路径')
        label = tk.Label(frame, text='')
        label.pack(side=tk.RIGHT)
        path_entry.pack(padx=15, side=tk.LEFT)
        path_entry.bind("<FocusOut>", lambda event: self.get_folder(path_entry, label))

    @staticmethod
    def label_frame(frame, y, x, text):
        """
        创建容器
        :param frame:
        :param y:
        :param x:
        :param text:
        :return:
        """
        frame = tk.Frame(frame)
        frame.place(y=y, x=x)

        label = tk.Label(frame, text=f"{text}:")
        label.pack(pady=0, side=tk.LEFT)
        return frame

    def show_ocr_info(self):
        """
        ocr信息
        :return:
        """
        frame = self.label_frame(self.control_set.get("top_content"), 85, 0, "识别")
        tk.Label(frame, text="ocr识别字体：", width=10, fg="gray").pack(pady=2, side=tk.LEFT)
        font_label = tk.Label(frame, text="-", width=3, fg="black")
        font_label.pack(pady=0, side=tk.LEFT)
        tk.Label(frame, text="字体置信度：", width=10, fg="gray").pack(pady=4, side=tk.LEFT)
        cond_label = tk.Label(frame, text="0.0", width=3, fg="black")
        cond_label.pack(pady=0, side=tk.LEFT)
        self.control_set.update({"font_label": font_label, "cond_label": cond_label, })
        button = tk.Button(frame, text="忽略")
        button.pack(pady=0, side=tk.LEFT)
        button.bind("<Button-1>", lambda event: self.ignor_img())

    def input_box_font(self):
        """
        输入字体
        :return:
        """
        frame = self.label_frame(self.control_set.get("top_content"), 120, 0, "汉字")

        def on_input_change(*args):
            value = var.get()
            if value == '请输入一个汉字，并按下回车键':
                var.set(value)
            elif len(value) > 1:
                var.set(value[0])

        var = tk.StringVar()
        var.trace_add("write", on_input_change)

        entry = tk.Entry(frame, width=15, textvariable=var)
        self.input_tip(entry, '请输入一个汉字，并按下回车键')

        entry.pack(pady=0, padx=15, side=tk.LEFT)
        entry.bind("<Return>", lambda event: self.input_char(entry))
        entry.focus_set()
        self.control_set.update({"font_box": entry})

        button = tk.Button(frame, text="确认")
        button.pack(pady=0, side=tk.LEFT)
        button.bind("<Button-1>", lambda event: self.input_char(entry))

        button = tk.Button(frame, text="打开文件夹", command=self.open_file_explorer)
        button.pack(pady=0, side=tk.LEFT)

    def open_file_explorer(self):
        if os.name == 'nt':
            Popen(f'explorer "{self.folder_path}"')
        elif os.name == 'posix':
            Popen(['open', self.folder_path])
        else:
            self.logger.warn("Unsupported operating system")

    def create_image_grid(self):
        """
        图片集展示
        :param image_frame:
        :return:
        """
        # 只取前 n 张
        for widget in self.control_set.get("img_content").winfo_children():
            widget.destroy()
        num_images = len(self.images)
        cols = ceil(sqrt(num_images))  # 自动计算列数（正方形布局）
        for i, path in enumerate(self.images):
            row = i // cols
            col = i % cols
            pil_img = Image.open(os.path.join(self.folder_path, path))
            pil_img.thumbnail((200, 200), Image.Resampling.LANCZOS)  # 缩略图大小
            tk_img = ImageTk.PhotoImage(pil_img)

            label = tk.Label(self.control_set.get("img_content"), image=tk_img, relief="groove")
            label.image = tk_img  # ⚠️ 防止被回收
            label.grid(row=row, column=col, padx=5, pady=5)

    def show_choice(self, flag):
        self.flag = flag
        self.get_image_list()

    def check_box(self):
        """
        处理图片方法
        :return:
        """
        frame = self.label_frame(self.control_set.get("top_content"), 50, 0, "操作")
        # 创建单选框
        auto_box = tk.Radiobutton(frame, text="自动选图", pady=10, value=1,
                                  command=lambda: self.show_choice(True))
        auto_box.pack(anchor="w", side=tk.LEFT)
        signal_box = tk.Radiobutton(frame, pady=10, text="点选选图", value=2,
                                    command=lambda: self.show_choice(False))
        signal_box.pack(anchor="w", side=tk.LEFT)

        # 创建变量（IntVar 或 StringVar）
        var = tk.IntVar()
        check_ = tk.Checkbutton(frame, text="是否启用识别", variable=var, onvalue=1, offvalue=0)
        check_.pack(side=tk.LEFT)
        check_.bind("<Button-1>", lambda event: self.enable_recognition(var))

    def enable_recognition(self, var):
        """
        获取ocr对象
        :param var:
        :return:
        """
        if var.get() == 0:
            self.reader = easyocr.Reader(['ch_sim', 'ch_tra'], gpu=True, detect_network='craft', recog_network='zh_sim_g2',
                                         cudnn_benchmark=True, quantize=True, model_storage_directory="./model"
                                         # 启用量化优化推理速度
                                         )
        else:
            self.control_set.get("font_label").config(text='')
            self.control_set.get("cond_label").config(text='', bg=None)

    def get_folder(self, event, label):
        """
        获取文件夹路径
        :param label:
        :param event:
        :return:
        """
        var = False
        path = event.get().strip()
        try:
            folder_path = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
            if os.path.exists(folder_path):
                if os.path.isdir(folder_path):
                    self.folder_path = folder_path
                    if os.path.isdir(self.folder_path):
                        self.control_set.get("label_total").config(text=f"总计：{len(os.listdir(self.folder_path))}")
                    var = True
                else:
                    self.logger.error("该路径非文件夹：", folder_path)
            else:
                self.logger.error("错误", f"路径 '{path}' 不是一个有效路径或者路径不存在。")
        except Exception as e:
            self.logger.error("错误", f"检查路径 '{path}' 时发生异常。异常信息：{e}")
        finally:
            label.config(text=f"√" if var else "×", bg="lightgreen" if var else "red")

    def move_images_to_folder(self, folder_path: str):
        """
        文件移动
        :param folder_path:
        :return:
        """
        os.makedirs(folder_path, exist_ok=True)
        for image in self.images:
            new_img_path = os.path.join(folder_path, os.path.basename(image))
            move(image, new_img_path)
            self.logger.info(f"Image moved to {new_img_path}")
        self.control_set.get("label_leave").config(text=f"剩余：{len(os.listdir(self.folder_path))}")

    @staticmethod
    def read_clipboard_images():
        """
        剪切板数据源
        :return:
        """
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
                return list(win32clipboard.GetClipboardData(win32clipboard.CF_HDROP))
            win32clipboard.EmptyClipboard()
        except BaseException as e:
            messagebox.showerror(e.__str__())
        finally:
            win32clipboard.CloseClipboard()
        return []

    def monitor_clipboard(self):
        """
        剪切板数据获取
        :return:
        """
        last_content = []
        while not self.flag:
            current = self.read_clipboard_images()
            if current != last_content and current:
                last_content = current
                self.images = [f for f in current if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))][
                              :25]
                self.create_image_grid()
                self.discriminate_img()
            sleep(1)  # 每秒检查一次

    def listen_thread(self):
        """
        创建一个监听线程，监听ctrl+c
        :return:
        """
        # 创建并启动一个线程
        if not self.flag:
            test_thread = Thread(target=self.monitor_clipboard, name="OCR_识别线程")
            test_thread.start()

    def get_image_list(self):
        """
        获得并展示图片列表
        :return:
        """
        if self.flag:
            self.auto_show_img()
        else:
            self.listen_thread()

    def auto_show_img(self):
        """
        自动展示下张图片
        :return:
        """
        if self.flag:
            if "已分类" in self.folder_path:
                if self.folder_path.endswith("已分类"):
                    folder_list = os.listdir(self.folder_path)
                    folder_path = os.path.join(self.folder_path, folder_list[0]) if folder_list else None
                    index = 0
                else:
                    folder = os.path.split(self.folder_path)
                    folder_list = os.listdir(folder[0])
                    index = folder_list.index(folder[1])+1
                    index = index if index < len(folder_list) else 0
                    folder_path = os.path.join(folder[0], folder_list[index])
                self.control_set.get("font_box").insert(0, folder_path[-1] if folder_path else None)
                self.folder_path = folder_path if folder_path else self.folder_path
                image_list = [os.path.join(folder_path, i) for i in os.listdir(folder_path)] if folder_path else []
                self.control_set.get("label_leave").config(text=f"剩余：{len(folder_list) - index}")
            else:
                image_list = os.listdir(self.folder_path)
                image_list = [os.path.join(self.folder_path, image_list[0])] if image_list else []
            self.images = [f for f in image_list if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))][:25]
            self.create_image_grid()
            self.discriminate_img()
        else:
            pass

    def ignor_img(self):
        """
        处理无法识别的图片
        :return:
        """
        if "已分类" not in self.folder_path:
            target_path = os.path.join(os.path.split(self.folder_path)[0], "未分类")
            os.makedirs(target_path, exist_ok=True)
            self.move_images_to_folder(os.path.join(target_path))
            self.auto_show_img()

    def input_char(self, event):
        """
        图片进行汉字打标
        :param event:
        :return:
        """
        user_input = event.get() or self.control_set.get("font_label").cget("text")
        if self.is_all_chinese(user_input):
            target_path = os.path.join(os.path.split(self.folder_path)[0], "已分类")
            tip = f"是否剪切图片到:{target_path}？"
            if "已分类" not in self.folder_path and messagebox.askokcancel("确认剪切", tip):
                os.makedirs(target_path, exist_ok=True)
                self.move_images_to_folder(os.path.join(target_path, f'chapter_{user_input}'))
            event.delete(0, tk.END)  # 清除输入框的文字
            self.auto_show_img()
        else:
            messagebox.showwarning("警告", "仅支持输入中文汉字")

    def run(self):
        self.logger.info("程序启动")
        self.ui_layout()
        self.root.mainloop()
        self.logger.info("程序结束")


if __name__ == '__main__':
    ImageLabel().run()
