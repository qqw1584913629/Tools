import os
import tkinter as tk
from tkinter import filedialog
from qcloud_cos import CosConfig, CosS3Client
import hashlib
import json
import threading
from tkinter.ttk import Progressbar

def update_progress_bar(uploaded):
    progress['value'] = uploaded

def select_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        local_dir_entry.delete(0, tk.END)
        local_dir_entry.insert(0, folder_selected)

def load_config():
  with open('config.json') as f:
    config = json.load(f)
    secret_id = config['secret_id']
    secret_key = config['secret_key']
    region = config['region']
    bucket = config['bucket']
    cos_path = config['cos_path']
    
    prefix_var3.set(secret_id)
    prefix_var4.set(secret_key)
    prefix_var5.set(region)
    prefix_var2.set(bucket)
    prefix_var.set(cos_path)


def read_json():
    load_config()

def sync_files():
    local_dir = local_dir_entry.get()
    prefix = prefix_var.get().strip()
    bucket = prefix_var2.get().strip()

    # 这里添加你的 COS 配置和同步逻辑
    secret_id = prefix_var3.get().strip()
    secret_key = prefix_var4.get().strip()
    region = prefix_var5.get().strip()
    if not local_dir or not prefix or not bucket or not secret_id or not secret_key or not region:
        tk.messagebox.showwarning('警告', '请确保所有信息都已填写')
        return
    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    client = CosS3Client(config)

    # 获取本地文件信息
    local_files = {}
    for root, _, files in os.walk(local_dir):
        for name in files:
            path = os.path.join(root, name)
            md5 = hashlib.md5(open(path,'rb').read()).hexdigest()  
            local_files[path] = {
                'name': name,
                'md5': md5
            }
    # 获取COS文件信息  
    cos_files = {}
    contents = client.list_objects(Bucket=bucket, Prefix=prefix)['Contents']
    for item in contents:
        key = item['Key']
        cos_files[key] = {
            'name': key.split('/')[-1],
            'md5': item['ETag'].strip('"')
        } 

    # 需要上传差异化的文件
    upload_files = set()
    for path, attr in local_files.items():
        name = prefix + attr['name'].split('/')[-1]
        if name not in cos_files or cos_files[name]['md5'] != attr['md5']:
            upload_files.add(path)

    # 需要删除差异化的文件
    delete_files = set()
    for key, attr in cos_files.items():
        path = key[len(prefix):]
        key = os.path.join(local_dir, path)
        if key not in local_files or attr['md5'] != local_files[key]['md5']:
            delete_files.add(path)

    
    # 删除
    for file in delete_files:
        client.delete_object(Bucket=bucket, Key=prefix + file)

    global finished
    global total
    finished = 0
    total = len(upload_files)
    for file in upload_files:
        t = threading.Thread(target=upload_file, args=(file, prefix + (file.split('\\')[-1]), client, bucket))
        t.start()

# 上传函数
def upload_file(file, key, client, bucket):
    global finished
    client.put_object_from_local_file(
            Bucket=bucket,
            LocalFilePath=file,
            Key=key  
        )
    finished += 1
    root.after(100, update_progress_bar, int(finished / total * 100))
    if finished == total:
        tk.messagebox.showinfo('提示', '差异化更新资源成功!') 


# 创建主窗口
root = tk.Tk()
root.title("腾讯云COS资源文件差异更新工具")
# 设置窗体初始大小为500x500像素
root.geometry("500x500")
# 计算屏幕中心位置
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width - 500) // 2
y = (screen_height - 500) // 2
root.geometry(f"500x500+{x}+{y}")


progress = Progressbar(root, orient="horizontal", length=500, mode="determinate")
progress.pack()

local_dir_label4 = tk.Label(root, text="Secret_id:")
local_dir_label4.pack()
prefix_var3 = tk.StringVar()
prefix_entry3 = tk.Entry(root, width=40, textvariable=prefix_var3)
prefix_entry3.pack()
prefix_entry3.configure(show=prefix_var3.get())

local_dir_label5 = tk.Label(root, text="Secret_key:")
local_dir_label5.pack()
prefix_var4 = tk.StringVar()
prefix_entry4 = tk.Entry(root, width=40, textvariable=prefix_var4)
prefix_entry4.pack()
prefix_entry4.configure(show=prefix_var4.get())

local_dir_label6 = tk.Label(root, text="Region:")
local_dir_label6.pack()
prefix_var5 = tk.StringVar()
prefix_entry5 = tk.Entry(root, width=40, textvariable=prefix_var5)
prefix_entry5.pack()
prefix_entry5.configure(show=prefix_var5.get())

local_dir_label3 = tk.Label(root, text="存储桶:")
local_dir_label3.pack()
prefix_var2 = tk.StringVar()
prefix_entry2 = tk.Entry(root, width=40, textvariable=prefix_var2)
prefix_entry2.pack()
prefix_entry2.configure(show=prefix_var2.get())

# 添加输入框和标签
local_dir_label = tk.Label(root, text="本地目录:")
local_dir_label.pack()
local_dir_entry = tk.Entry(root, width=40)
local_dir_entry.pack()
select_button = tk.Button(root, text="选择文件夹", command=select_folder)
select_button.pack()

local_dir_label2 = tk.Label(root, text="COS远程目录:")
local_dir_label2.pack()
prefix_var = tk.StringVar()
prefix_entry = tk.Entry(root, width=40, textvariable=prefix_var)
prefix_entry.pack()
prefix_entry.configure(show=prefix_var.get())


# 添加按钮
sync_button = tk.Button(root, text="开始差异更新", command=sync_files)
sync_button.pack()

# 添加按钮
sync_button = tk.Button(root, text="加载Json配置文件", command=read_json)
sync_button.pack()

# 启动主循环
root.mainloop()
