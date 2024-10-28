# Background Eraser

大量の画像を背景透過するためのツールです。  
U2Netを使用して背景を透過しますが、手動での修正も可能です。  
主にAIの学習データを作成するために使用します。

[English](README.md) | 日本語

<img src="image/README/1730130814363.png" width="48%">
<img src="image/README/1730131090907.png" width="48%">

## 使い方

```bash
git clone https://github.com/fa0311/background_erase.git
cd background_erase
pip install -r requirements.txt
python main.py
```

## 機能

### 操作

- **Previous** 前の画像に移動
- **Next** 次の画像に移動
- **Reload** 保存前の状態に戻す
- **Clear** 背景の透過を全て戻す
- **Include** 透過した画像をIncludeフォルダに保存
- **Exclude** 透過した画像をExcludeフォルダに保存
- **Background** 境界線を表示する
- **Auto** 全ての画像をU2Netで背景透過する

### 編集

- **View** 閲覧モード
- **Erase** 消しゴムによって背景を手動で削除
- **Pen** ペンによって消された背景を復元
- **RemFill** 周辺の色を参考にして背景を削除
- **UndoFill** 周辺の色を参考にして背景を復元
- **RemBg** U2Netによって背景を削除
- **UndoBg** U2Netによって削除された背景を復元

## ショートカット

- **Space** 透過した画像をIncludeフォルダに保存する
- **Left,A** 前の画像に移動
- **Right,D** 次の画像に移動
- **Z** セーブ前の状態に戻す
