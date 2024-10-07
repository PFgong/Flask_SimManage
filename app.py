from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify
import pandas as pd
from io import BytesIO

app = Flask(__name__)
# 模拟SIM卡数据
data = [{"id": i, "tel": "14223091771", "opt": "中国移动", "loc": "上海", "use": "重庆", "sta": "使用",
         "user": "pengfei.gong", "puk": "12345", "trf": "54元/月", "code": "WID12"} for i in range(1, 101)]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_data')
def data_route():
    # 获取分页参数
    page = int(request.args.get('page', 1))
    rows_per_page = int(request.args.get('rows_per_page', 10))
    start = (page - 1) * rows_per_page

    # 获取过滤参数：号码、运营商、归属地、使用地、使用状态、使用人、编号后五位
    tel_filter = request.args.get('tel', '').lower()
    opt_filter = request.args.get('opt', '').lower()
    loc_filter = request.args.get('loc', '').lower()
    use_filter = request.args.get('use', '').lower()
    sta_filter = request.args.get('sta', '').lower()
    user_filter = request.args.get('user', '').lower()
    code_filter = request.args.get('code', '').lower()

    # 表格数据
    filtered_data = data

    # 开始筛选
    if tel_filter:
        filtered_data = [item for item in filtered_data if tel_filter in item['tel'].lower()]
    if opt_filter:
        filtered_data = [item for item in filtered_data if opt_filter in item['opt'].lower()]
    if loc_filter:
        filtered_data = [item for item in filtered_data if loc_filter in item['loc'].lower()]
    if use_filter:
        filtered_data = [item for item in filtered_data if use_filter in item['use'].lower()]
    if sta_filter:
        filtered_data = [item for item in filtered_data if sta_filter in item['sta'].lower()]
    if user_filter:
        filtered_data = [item for item in filtered_data if user_filter in item['user'].lower()]
    if code_filter:
        filtered_data = [item for item in filtered_data if code_filter in item['code'].lower()]

    # 获取过来后的分页数据
    items = filtered_data[start:start + rows_per_page]
    total = len(filtered_data)
    return jsonify({'items': items, 'total': total})


@app.route('/import_sim', methods=['POST'])
def import_sim():
    global data
    if 'file' not in request.files:
        return jsonify({'message': '没有找到文件!'}), 400
    file = request.files['file']
    if not file.filename.endswith('.xlsx'):
        return jsonify({'message': '请上传一个有效的 Excel 文件!'}), 400
    try:
        # 读取Excel文件 - 检查是否包含所需列 (keep_default_na=False读取到空字符串时读出的就是''而不是nan)
        df = pd.read_excel(file, keep_default_na=False)
        required_columns = ['编号', '号码', '运营商', '归属地', '使用地', '使用状态', '使用人', 'PUK', '资费', '编号后五位']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'message': '缺少必要的列，请确保包含编号、号码、运营商、归属地、使用地、使用状态、使用人、PUK、资费、编号后五位!'}), 400

        max_id = max([item['id'] for item in data]) if data else 0  # 获取数据库最大id -- 当前为字典模拟，实际用数据库唯一性来实现
        ins = 1
        # 更新数据 - 号码和ID唯一性（若有相同的号码：ID保留数据库的, 其他信息覆盖; 若不同的号码: ID从数据库最大开始累加赋值）
        for _, row in df.iterrows():
            id_ = row['编号']
            tel_ = row['号码']
            opt = row['运营商']
            loc = row['归属地']
            use = row['使用地']
            sta = row['使用状态']
            user = row['使用人']
            puk = row['PUK']
            trf = row['资费']
            code = row['编号后五位']

            existing_index = next((index for index, item in enumerate(data) if str(item['tel']).strip() == str(tel_).strip()), None)
            # 检查号码是否存在数据库
            if existing_index is not None:
                # 存在：更新覆盖
                data[existing_index].update({"opt": opt, "loc": loc, "use": use,
                                             "sta": sta, "user": user, "puk": puk,
                                             "trf": trf, "code": code})
            else:
                # 不存在：更新添加
                id_ = int(max_id) + ins
                ins = ins + 1
                data.append({"id": id_, "tel": tel_, "opt": opt, "loc": loc, "use": use,
                             "sta": sta, "user": user, "puk": puk, "trf": trf, "code": code})
        total_count = len(data)
        return jsonify({'success': True, 'message': '导入成功', 'total': total_count}), 200
    except Exception as e:
        return jsonify({'message': f'导入失败: {str(e)}'}), 500


@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    global data
    data = [d for d in data if d['id'] != id]
    return redirect(url_for('index'))


@app.route('/borrow/<int:id>', methods=['POST'])
def borrow_sim(id):
    global data
    for d in data:
        if d['id'] == id:
            d['user'] = "user"
            d['sta'] = "使用"
            break
    return jsonify(message='SIM卡借用成功')


@app.route('/return/<int:id>', methods=['POST'])
def return_sim(id):
    global data
    for d in data:
        if d['id'] == id:
            d['user'] = ""
            d['sta'] = "空闲"
            break
    return jsonify(message='SIM卡归还成功')


@app.route('/edit_sim/<int:id>', methods=['POST'])
def edit_sim(id):
    global data
    edit_tel = request.form['tel']
    edit_opt = request.form['opt']
    edit_loc = request.form['loc']
    edit_use = request.form['use']
    edit_sta = request.form['sta']
    edit_user = request.form['user']
    edit_puk = request.form['puk']
    edit_trf = request.form['trf']
    edit_code = request.form['code']

    for d in data:
        if d['id'] == id:
            if str(edit_tel).strip() != d['tel'].strip():
                existing_index = next(
                    (index for index, item in enumerate(data) if str(item['tel']).strip() == str(edit_tel).strip()), None)
                if existing_index is not None:
                    return jsonify({'success': False, 'message': 'Data ID-{} updated fail, tel number is exist.'.format(id)})
            d['tel'] = edit_tel
            d['opt'] = edit_opt
            d['loc'] = edit_loc
            d['use'] = edit_use
            d['sta'] = edit_sta
            d['user'] = edit_user
            d['puk'] = edit_puk
            d['trf'] = edit_trf
            d['code'] = edit_code
            break
    return jsonify({'success': True, 'message': 'Data ID-{} updated successfully'.format(id)})


@app.route('/insert_sim', methods=['POST'])
def insert_sim():
    global data
    insert_tel = request.form['tel']
    insert_opt = request.form['opt']
    insert_loc = request.form['loc']
    insert_use = request.form['use']
    insert_sta = request.form['sta']
    insert_user = request.form['user']
    insert_puk = request.form['puk']
    insert_trf = request.form['trf']
    insert_code = request.form['code']

    max_id = max([item['id'] for item in data]) if data else 0
    existing_index = next(
        (index for index, item in enumerate(data) if str(item['tel']).strip() == str(insert_tel).strip()), None)

    if existing_index is not None:
        return jsonify({'success': False, 'message': 'SIM data insert fail, tel number is exist.'})
    else:
        print(insert_tel)
        data.append({"id": int(max_id)+1, "tel": insert_tel, "opt": insert_opt, "loc": insert_loc, "use": insert_use,
                     "sta": insert_sta, "user": insert_user, "puk": insert_puk, "trf": insert_trf, "code": insert_code})
        total_count = len(data)
        return jsonify({'success': True, 'message': 'SIM data inserted successfully', 'total': total_count}), 200


@app.route('/export_sim')
def export():
    df = pd.DataFrame(data)
    df.columns = ['编号', '号码', '运营商', '归属地', '使用地', '使用状态', '使用人', 'PUK', '资费', '编号后五位']
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='sim_table')
    writer._save()
    output.seek(0)
    # 响应
    response = make_response(output.read())
    response.headers['Content-Disposition'] = 'attachment; filename=sims.xlsx'
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


if __name__ == '__main__':
    app.run(debug=True)
