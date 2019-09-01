var config = {
    mdPath:"E:/blog/wizmd/",
    imgPath:"E:/blog/wizmd/index_files/",
    showRootDir: false, 
    useEditorMd: true 
}

function OnExportMDButtonClicked() {
    // var objBrowser = WizExplorerApp.Window.CurrentDocumentBrowserObject;
    // objBrowser.ExecuteScript("document.body.innerText", function(docText) {
    //     objWindow.ShowMessage("文档内容为空, 导出失败" + docText, "提示", 0x40);
    // });

    var objApp = WizExplorerApp,
        objWindow = objApp.Window,
        objDocument = objWindow.CurrentDocument,
        objCommon = objApp.CreateWizObject("WizKMControls.WizCommonUI"),
        tempDocument = getTempDocumentInfo(objCommon, objDocument, objApp);

    if (!tempDocument.text) {
        objWindow.ShowMessage("文档内容为空, 导出失败", "提示", 0x40);
        return false;
    }

    tempDocument.text = modifyDocument(objCommon, objDocument, tempDocument.text);
    saveFile(objCommon, objDocument, objWindow, tempDocument);
}

function getTempDocumentInfo(objCommon, objDocument, objApp) {
    var tempPath = objCommon.GetSpecialFolder("TemporaryFolder") + "export_md_temp/";
    objCommon.CreateDirectory(tempPath);

    tempPath += objDocument.GUID + "/";
    objCommon.CreateDirectory(tempPath);

    var tempImgPath = tempPath + "index_files/",
        tempFile = tempPath + "index.html";
        locationHref = tempFile + '?guid=' + objDocument.GUID + "&kbguid=" + objDocument.Database.KbGUID;

    objCommon.CreateDirectory(tempImgPath);
    objDocument.SaveToHtml(tempFile, 0);
    if (config.useEditorMd){
        var code = loadDocument(objApp, objWindow, locationHref);
    }
    else {
        var code = convertHtmlToText(objCommon.LoadTextFromFile(tempFile));
    }

    return {
        text: code, 
        imagePath: tempImgPath
    }
}

function convertHtmlToText(text) {
    var match = text.match('<body>(.*)</body>');
    text = match[1];
    text = text.replace(/<br\/>/gm, '\n');
    text = text.replace(/&lt;/gm, '<');
    text = text.replace(/&gt;/gm, '>');

    return text;
}

function modifyDocument(objCommon, objDocument, text) {
    text = setHeadInfo(objCommon, objDocument, text);
    text = setImagePath(text);
    text = deleteEdtag(text);
    return text;
}

function setImagePath(text) {
    return text.replace(/index_files/g,"index_files");
}

function deleteDescLabel(text) {
    return  text = text.replace(/---[\s\S]*?---/gm, '')
}

function deleteEdtag (text) {
    //fix unuseful content bug
    return text.replace(/<ed_tag.*?<\/ed_tag>/g, '');
}

function setHeadInfo(objCommon, objDocument, text) {
    var categories = objDocument.Parent.Name,
        dtCreated = new Date(objDocument.DateCreated),
        timeCreated = objCommon.ToLocalDateString(dtCreated, false) + " " + objCommon.ToLocalTimeString(dtCreated),
        dtModified = new Date(objDocument.DateModified),
        timeModified = objCommon.ToLocalDateString(dtModified, false) + " " + objCommon.ToLocalTimeString(dtModified),
        location = objDocument.Location;

    if (config.showRootDir) {
        if (location.match(/^\/([\w-]+)\/?/)) {
            categories = location.match(/^\/([\w-\s]+)\/?/)[1]
        }
    }
    else {
        // 将路径中的 / 替换为 ",", 然后裁剪到开头结尾的逗号，最后替换 "," 为 ", "
        categories = location.replace(/\//g,",").slice(1,-1).replace(/\,/g,", ")
    }
    
    var head = addHeadToDocument(text, {
        title: objDocument.Title.replace(/\.md$/g, ''),
        tags: objDocument.Tags,
        date: timeCreated,
        updated: timeModified, 
        categories: categories
    })

    text = deleteDescLabel(text)

    text = head + text;
    return text;
}

function saveFile(objCommon, objDocument, objWindow, tempDocument) {
    //save file
    var filename = config['mdPath'] + objDocument.Title.replace(/\.md$/g, '') + ".md";
    objCommon.SaveTextToFile(filename, tempDocument.text, "utf-8");

    //save image. copy file from tempory to target folder 复制图片
    var path = objCommon.EnumFiles2(tempDocument.imagePath, "*.*", false);
    if(!path) {
        objWindow.ShowMessage("文档无图片，导出完成", "提示", 0x40);
        return true;
    }

    var imgPath = config['imgPath'],
        pathArr = path.split("\n"),
        len = pathArr.length,
        curPath = "",
        name = "";

    for (var i = 0; i< len; i++) {
        curPath = pathArr[i];
        name = curPath.substring(curPath.lastIndexOf("/") + 1, curPath.length);;
        curPath = imgPath + name;
        objCommon.CopyFile(pathArr[i], curPath);
    }

    objWindow.ShowMessage("文档有图片，导出完成", "提示", 0x40);
}

function addHeadToDocument(text, docInfo){
    var tags, moreLabels;

    //tags
    var ret = [];
    for (var i = 0; i < docInfo.tags.Count; i++) {
        ret.push(docInfo.tags.Item(i).Name);
    }

    tags = ret.join(", ");

    var exec = /---([\s\S]*?)---/gm.exec(text)

    moreLabels = exec ? exec[1].replace(/^\s*|\s*$/g, '').replace(/!\[\]\((.*?)\)/g, '$1') : '';
    //morelabels
    if (moreLabels) {
        var encodeLabels = encodeURIComponent(moreLabels);
        encodeLabels = encodeLabels.replace(/%3A%C2%A0/g, '%3A%20')
        moreLabels = decodeURIComponent(encodeLabels);
    }

    moreLabels = moreLabels || '\n';

    var head = "---" + "\n"
            + "title: " + docInfo.title + "\n"
            + "date: " + docInfo.date + "\n"
            + "updated: " + docInfo.updated + "\n"
            + "categories: [" + docInfo.categories + "]\n"
            + "tags: [" + tags + "]\n"
            + "copyright: " + "true" + "\n"
            + "mathjax: " + "true" + "\n"
            + "---" + "\n\n";

    return head;
}

////////////////////////////////////////////////
// 解析参数
function getQueryString(name, hrefValue) {
    if (hrefValue.indexOf("?") == -1 || hrefValue.indexOf(name + '=') == -1) {
        return '';
    }
    var queryString = hrefValue.substring(hrefValue.indexOf("?") + 1);

    var parameters = queryString.split("&");

    var pos, paraName, paraValue;
    for (var i = 0; i < parameters.length; i++) {
        pos = parameters[i].indexOf('=');
        if (pos == -1) { continue; }

        paraName = parameters[i].substring(0, pos);
        paraValue = parameters[i].substring(pos + 1);

        if (paraName == name) {
            return unescape(paraValue.replace(/\+/g, " "));
        }
    }
    return '';
};

// 加载文档
function loadDocument(objApp, objWindow, locationHref) {
    // var objApp = window.external;
    var objDatabase = null;
    var filesDirName = "index_files/";  // 本地文件目录名，不可更改
    var guid = getQueryString("guid", locationHref);
    var kbGUID = getQueryString("kbguid", locationHref);
    if (kbGUID == "" || kbGUID == null) {
        objDatabase = objApp.Database;
    }
    else {
        objDatabase = objApp.GetGroupDatabase(kbGUID);
    }

    var code = "";
    try {
        objDocument = objDatabase.DocumentFromGUID(guid);
        docTitle = objDocument.Title;
        
        document.title = "编辑 " + objDocument.Title.replace(new RegExp(".md", "gi"), "");

        var content = objDocument.GetHtml();
        var tempBody = document.body.innerHTML;
        document.body.innerHTML = content;

        var imgs = document.body.getElementsByTagName('img');
        if(imgs.length){
            for (var i = imgs.length - 1; i >= 0; i--) {
                var pi = imgs[i];
                if(pi && pi.parentNode.getAttribute("name") != "markdownimage") {
                    var imgmd = document.createTextNode("![](" + pi.getAttribute("src") + ")");
                    $(pi).replaceWith(imgmd);
                }
            }
        }
        
        var links = document.body.getElementsByTagName('a');
        if(links.length){
            for (var i = links.length - 1; i >= 0; i--) {
                var pi = links[i];
                if(pi && pi.getAttribute("href").indexOf("wiz://open_") != -1) {
                    var linkmd = document.createTextNode("[" + pi.textContent + "](" + pi.getAttribute("href") + ")");
                    $(pi).replaceWith(linkmd);
                }
            }
        }

        content = document.body.innerText;
        document.body.innerHTML = tempBody;
        code = content;

        /*code = objDocument.GetText(0);*/
        code = code.replace(/\u00a0/g, ' ');

        // 如果用原生编辑器保存过图片，会被替换成错的图片路径
        var imgErrorPath = guid + "_128_files/";
        code = code.replace(new RegExp(imgErrorPath, "g"), filesDirName);
    }
    catch (err) {
        objWindow.ShowMessage("err", "提示", 0x40);
    }

    return code;
};

function InitExoprtToMdButton() {
    var pluginPath = objApp.GetPluginPathByScriptFileName("ExportToMd.js");
    var languangeFileName = pluginPath + "plugin.ini";

    //strExport is key in plugin.ini file
    var buttonText = objApp.LoadStringFromFile(languangeFileName, "strExport");
    objWindow.AddToolButton("document", "ExportButton", buttonText, "", "OnExportMDButtonClicked");
}

InitExoprtToMdButton();
