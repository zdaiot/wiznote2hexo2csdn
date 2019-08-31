import re
import os
import shutil
import glob
import argparse

def deal_re_result(re_result, line, split_str):
    '''处理匹配出来的结果，得到当前行中所有图片的原始相对路径+名称

    Args：
        re_result: 由re.finditer寻找出的结果，以嵌套list给出
        line: 要处理的字符串
        split_str： 以什么符号分割出图片路径+名称

    return: 得到当前行中所有图片的原始相对路径+名称
    '''
    pics_ori_path_name = list()
    for index, pair in enumerate(re_result):
        if index == len(re_result)-1:
            pics_ori_path_name.append(line[pair[1]:].split(split_str)[0])
        else:
            pics_ori_path_name.append(line[pair[1]:re_result[index+1][0]].split(split_str)[0])
    return pics_ori_path_name

def get_pics_ori_path_name(pic_ori_path, line):
    '''对当前行进行正则化匹配，得到当前行中所有图片的原始相对路径+名称

    Args：
        pic_ori_path: 存放所有图片的原始路径
        line：当前行的字符串

    return: 得到当前行中所有图片的原始相对路径+名称
    '''
    if pic_ori_path in line:
        # 处理html格式的图片, 例如 <img  src="pic_ori_path/20180305105631792.jpg"  width = 30% height = 30% />
        if 'src=' in line:
            re_result = [[x.start(),x.end()] for x in re.finditer('src="', line)]
            pics_ori_path_name = deal_re_result(re_result, line, '"')
        # 处理markdown语法格式的图片
        else:
            # 查找所有的图片
            re_result = [[x.start(),x.end()] for x in re.finditer('!\[.*?]\(', line)]
            pics_ori_path_name = deal_re_result(re_result, line, ')')
        return pics_ori_path_name
    else: return None

def get_categories(data):
    '''从markdown文件的 categories 标签中得到目录，以'/'结尾

    Args：
        data：markdown文件的内容
    
    return:
        categories：markdown文件中的目录，以'/'结尾
        second_sign：markdown文件头部信息的结束位置
    '''
    before = [x for x in re.finditer(r'\-{3}', data)]
    second_sign = before[1].end()
    head_info = data[before[0].start():second_sign].split('\n')
    # 寻找目录
    for line in head_info:
        if 'categories' in line:
            re_result = [[x.start(),x.end()] for x in re.finditer('\[.*]', line)]
            tmp = line[re_result[0][0]+1:re_result[0][1]-1].split(',')
            tmp = [x.strip() for x in tmp]
            categories = '/'.join(tmp) + '/'
    return categories, second_sign

def get_qcloud_client(secret_id, secret_key, region, token=None):
    '''登录腾讯云对象存储，返回可上传图片的类。首先需要使用 `pip install -U cos-python-sdk-v5` 安装依赖
        具体内容在这里 https://github.com/tencentyun/cos-python-sdk-v5

    Args：
        secret_id: 用户的secret_id
        secret_key: 用户的secret_key
        region: 用户的region
        token: 使用临时秘钥需要传入Token，默认为空,可不填

    return: 可上传图片的类
    '''
    from qcloud_cos import CosConfig
    from qcloud_cos import CosS3Client
    from qcloud_cos import CosServiceError
    from qcloud_cos import CosClientError
    import logging, sys

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    # 设置用户属性, 包括secret_id, secret_key, region
    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token)  # 获取配置对象
    client = CosS3Client(config)
    print('client qcloud:', client)
    return client

def wiznote2hexo(path, pic_ori_path, mdfile_name):
    '''将为知笔记markdown文件中的图片路径`index_files`全部替换为markdown文件名，并将`index_files`文件夹重命名为markdown文件名。
        该方法适用于将手动从为知笔记导出的笔记转为hexo格式的笔记。
    
    Args：
        path: markdown文件的路径
        pic_ori_path: 存放所有图片的原始路径
        mdfile_name：markdown文件的名称
    
    return：None
    '''
    filepath = os.path.join(path + mdfile_name)
    # 以markdown的文件名(无后缀)建立文件夹放置图片
    pic_new_path = os.path.splitext(os.path.basename(mdfile_name))[0]
    os.rename('index_files', pic_new_path)

    with open(filepath, 'r', encoding='UTF-8') as fr:
        data = fr.read()
    lines = data.split('\n')
    for row, line in enumerate(lines):
        # 如果该行含有图片的话，这种方法不适用于html语法的图片，例如 <img  src="index_files/20180305105631792.jpg"  width = 30% height = 30% />
        # if re.match('!\[.*]\(', line):
        #     line = line.replace('index_files', pic_new_path)

        pics_ori_path_name = get_pics_ori_path_name(pic_ori_path, line)
        # 如果该行含有图片的话
        if pics_ori_path_name: 
            pics_ori_fullpath_name = [os.path.join(path, pic_ori_path_name) for pic_ori_path_name in pics_ori_path_name]
            for pic_ori_fullpath_name in pics_ori_fullpath_name:
                if not os.path.exists(pic_ori_fullpath_name):
                    print('picture {} 出现在Markdown文件中，但是不包含该图片'.format(pic_ori_fullpath_name.split('/')[-1]))

        # 替换该行中所有 pic_ori_path 为 pic_new_path，这要保证 pic_ori_path 在文章中只代表图片保存目录，没有特殊含义
        line = line.replace(pic_ori_path, pic_new_path)

        lines[row] = line
    head = '---\ntitle: {}\ndate:\ntags:\ncategories:\ncopyright: true\nmathjax:\n---\n'.format(pic_new_path)
    lines = [x+'\n' for x in lines]
    lines.insert(0,head) 
    with open(filepath, 'w', encoding='UTF-8') as fw:
        fw.writelines(lines)

def md2hexo(path, pic_ori_path, mdfile_path_name, save_path):
    '''将一个Markown文件中的图片路径更改为markdown文件名；建立以为markdown文件名命名的文件夹，并将该Markdown的所有图片移动到该文件夹。
        根据markdown文件中的 categories 建立文件夹，并将更改后的markdown文件和图片移动到该文件夹。
        该方法适用于 https://github.com/lzuliuyun/ExportToMd 从为知笔记导出的笔记转为hexo格式的笔记。

    Args：
        path: 存放markdown文件的根路径
        pic_ori_path: 存放所有图片的原始路径
        mdfile_path_name: 单个markdown的路径+名称
        save_path: markdown文件文件的保存根路径

    return：None
    '''
    print('Change markdown file {} to hexo', mdfile_path_name)
    # 以markdown的文件名(无后缀)建立文件夹放置图片
    mdfile_name = os.path.basename(mdfile_path_name)
    pic_new_path = os.path.splitext(mdfile_name)[0]

    with open(mdfile_path_name, 'r', encoding='UTF-8') as fr:
        data = fr.read()
    
    categories, second_sign = get_categories(data)
    # 建立保存markdown的路径
    mdfile_new_path = save_path + '/' + categories
    if not os.path.exists(mdfile_new_path):
        print('Making pth folder...')
        os.makedirs(mdfile_new_path)
    # 建立保存图片的路径
    if not os.path.exists(os.path.join(mdfile_new_path, pic_new_path)):
        print('Making pth folder...')
        os.makedirs(os.path.join(mdfile_new_path, pic_new_path))

    lines = data.split('\n')

    for row, line in enumerate(lines):
        pics_ori_path_name = get_pics_ori_path_name(pic_ori_path, line)
        # 如果该行含有图片的话
        if pics_ori_path_name: 
            pics_ori_fullpath_name = [os.path.join(path, pic_ori_path_name) for pic_ori_path_name in pics_ori_path_name]
            # 移动所有的图片，若图片不存在，则抛出异常
            for pic_ori_fullpath_name in pics_ori_fullpath_name:
                try:
                    pic_new_fullpath_name = pic_ori_fullpath_name.replace(path, mdfile_new_path)
                    pic_new_fullpath_name = pic_new_fullpath_name.replace(pic_ori_path, pic_new_path)
                    shutil.move(pic_ori_fullpath_name, pic_new_fullpath_name)
                except IOError as e:
                    if os.path.exists(pic_new_fullpath_name): print('图片 {} 已经移动，可能引用了相同的图片'.format(pic_new_fullpath_name.split('/')[-1]))
                    else: print(e)
            line = line.replace(pic_ori_path, pic_new_path)
            lines[row] = line
    lines = [x+'\n' for x in lines]

    with open(os.path.join(mdfile_new_path, mdfile_name), 'w', encoding='UTF-8') as fw:
        fw.writelines(lines)
    
def markdown2hexo(path, pic_ori_path, save_path):
    '''将一个文件夹下的所有Markown文件中的图片路径更改为markdown文件名；建立以为markdown文件名命名的文件夹，并将该Markdown的所有图片移动到该文件夹。
        根据markdown文件中的 categories 建立文件夹，并将更改后的markdown文件和图片移动到该文件夹。
        该方法适用于 https://github.com/lzuliuyun/ExportToMd 从为知笔记导出的笔记转为hexo格式的笔记。
    
    Args：
        path: 存放markdown文件的路径
        pic_ori_path: 存放所有图片的路径
        save_path: markdown文件文件的保存根路径

    return：None
    '''
    mds_fullpath_name = glob.glob(path + '/*.md')
    for md_fullpath_name in mds_fullpath_name:
        md2hexo(path, pic_ori_path, md_fullpath_name, save_path)
        
def hexomd2csdn(path, mdfile_path_name, save_path, use_qcloud, site_url, secret_id, secret_key, region, token=None, Bucket=None):
    '''将markdown文件中的本地图片路径全部替换为远程图片路径，适用于hexo博客中的markdown文件

    Args：
        path: 存放markdown文件的根路径
        mdfile_path_name：markdown文件的路径+名称
        save_path: markdown文件文件的保存根路径
        use_qcloud: 是否使用腾讯云对象存储；若为0则使用site_url，否则使用腾讯云
        site_url: 网站的名称+'/'，当use_qcloud为0是，这个不能为空
        secret_id: 用户的secret_id，当use_qcloud为1是，这个不能为空
        secret_key: 用户的secret_key，当use_qcloud为1是，这个不能为空
        region: 用户的region，当use_qcloud为1是，这个不能为空
        token: 使用临时秘钥需要传入Token，默认为空,可不填
        Bucket：用于的存储桶名称，当use_qcloud为1是，这个不能为空

    return：None
    '''
    print('Change hexo markdown file {} to csdn', mdfile_path_name)
    mdfile_name = os.path.basename(mdfile_path_name)
    pic_ori_path = os.path.splitext(mdfile_name)[0]

    with open(mdfile_path_name, 'r', encoding='UTF-8') as fr:
        data = fr.read()
    
    categories, second_sign = get_categories(data)
    # 去掉头部信息
    data = data[second_sign:].strip() # strip() 用于移除字符串头尾指定的字符（默认为空格或换行符）
    
    if use_qcloud:
        client = get_qcloud_client(secret_id, secret_key, region, token=token)

    lines = data.split('\n')
    # 开始处理每一行数据
    for row, line in enumerate(lines):
        pics_ori_path_name = get_pics_ori_path_name(pic_ori_path, line)
        # 如果该行中含有图片的话，将所有图片的路径更换为新的地址
        if pics_ori_path_name:
            # 若使用腾讯云对象存储
            if use_qcloud:
                # 上传该行中的每一张图片
                for pic_ori_path_name in  pics_ori_path_name:
                    try:
                        # 本地路径 简单上传
                        response = client.put_object_from_local_file(
                            Bucket=Bucket,
                            LocalFilePath=pic_ori_path_name,
                            Key=pic_ori_path_name,
                        )
                        print('up:', response['ETag'])

                        # 得到下载地址
                        response = client.get_presigned_download_url(
                            Bucket=Bucket,
                            Key=pic_ori_path_name
                        )
                        print('geturl:', response)
                        line = line.replace(pic_ori_path_names, response)
                    except:
                        print('Upload image {} Error'.format(pic_ori_path_name))
            # 若使用 site_url 链接
            else:
                line = line.replace(pic_ori_path, site_url + categories + pic_ori_path)
            lines[row] = line

    lines = [x+'\n' for x in lines]
    onemorething = ['\r\n','---\n','## One more thing\n','更多关于人工智能、Python、C++、计算机等知识，欢迎访问我的个人博客进行交流， [点这里~~](https://www.zdaiot.com)']
    lines = lines + onemorething

    mdfile_new_path = os.path.dirname(mdfile_path_name).replace(path, save_path)
    if not os.path.exists(mdfile_new_path):
        print('Making pth folder...')
        os.makedirs(mdfile_new_path)
    with open(os.path.join(mdfile_new_path, mdfile_name), 'w', encoding='UTF-8') as fw:
        fw.writelines(lines)

def hexomarkdown2csdn(path, save_path, use_qcloud, site_url, secret_id, secret_key, region, token=None, Bucket=None):
    '''将path路径下的所有markdown文件中的本地图片路径全部替换为远程图片路径；适用于将hexo博客中的markdown文件转换为csdn格式的

    Args：
        path: 存放markdown文件的根路径
        save_path: markdown文件文件的保存根路径
        use_qcloud: 是否使用腾讯云对象存储；若为0则使用site_url，否则使用腾讯云
        site_url: 网站的名称+'/'，当use_qcloud为0是，这个不能为空
        secret_id: 用户的secret_id，当use_qcloud为1是，这个不能为空
        secret_key: 用户的secret_key，当use_qcloud为1是，这个不能为空
        region: 用户的region，当use_qcloud为1是，这个不能为空
        token: 使用临时秘钥需要传入Token，默认为空,可不填
        Bucket：用于的存储桶名称，当use_qcloud为1是，这个不能为空

    return：None
    '''
    if use_qcloud:
        assert secret_id != None
        assert secret_key != None
        assert region != None
        assert Bucket != None
    else:
        assert site_url != None

    for root, dirs, files in os.walk(path):
        print("root", root)  # 当前目录路径
        print("dirs", dirs)  # 当前路径下所有子目录
        print("files", files)  # 当前路径下所有非目录子文件
        for myfile in files:
            if os.path.splitext(myfile)[1] == '.md':
                mdfile_path_name = os.path.join(root, myfile)
                hexomd2csdn(path, mdfile_path_name, save_path, use_qcloud, site_url, secret_id, secret_key, region, token=None, Bucket=Bucket)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', type=str, default='', help='存放markdown文件的根路径.')
    parser.add_argument('--pic_ori_path', type=str, default='index_files', help='用于的存储桶名称，当use_qcloud为1是，这个不能为空.')
    parser.add_argument('--mdfile_name', type=str, default='', help='markdown文件的名称.')
    parser.add_argument('--mdfile_path_name', type=str, default='', help='单个markdown的路径+名称.')
    parser.add_argument('--save_path', type=str, default='', help='markdown文件文件的保存根路径.')
    parser.add_argument('--use_qcloud', type=str, default='', help='是否使用腾讯云对象存储；若为0则使用site_url，否则使用腾讯云上.')
    parser.add_argument('--site_url', type=str, default='www.zdaiot.com/', help='网站的名称+'/'，当use_qcloud为0是，这个不能为空.')
    parser.add_argument('--secret_id', type=str, default='', help='用户的secret_id，当use_qcloud为1是，这个不能为空.')
    parser.add_argument('--secret_key', type=str, default='', help='用户的secret_key，当use_qcloud为1是，这个不能为空.')
    parser.add_argument('--region', type=str, default='', help='用户的region，当use_qcloud为1是，这个不能为空.')
    parser.add_argument('--token', type=str, default='', help='使用临时秘钥需要传入Token，默认为空,可不填.')
    parser.add_argument('--Bucket', type=str, default='', help='用于的存储桶名称，当use_qcloud为1是，这个不能为空.')
    parser.add_argument('--mode', type=str, default='', help='wiznote2hexo/md2hexo/markdown2hexo/hexomd2csdn/hexomarkdown2csdn.')
    config = parser.parse_args()

    if config.mode == 'wiznote2hexo':
        wiznote2hexo(config.path, config.pic_ori_path, config.mdfile_name)
    elif config.mode == 'md2hexo':
        md2hexo(config.path, config.pic_ori_path, config.mdfile_path_name, config.save_path)
    elif config.mode == 'markdown2hexo':
        markdown2hexo(config.path, config.pic_ori_path, config.save_path)
    elif config.mode == 'hexomd2csdn':
        hexomd2csdn(config.path, config.mdfile_path_name, config.save_path, config.use_qcloud, config.site_url, config.secret_id, \
            config.secret_key, config.region, token=config.token, Bucket=config.Bucket)
    elif config.mode == 'hexomarkdown2csdn':
        hexomarkdown2csdn(config.path, config.save_path, config.use_qcloud, config.site_url, config.secret_id, \
            config.secret_key, config.region, token=config.token, Bucket=config.Bucket)