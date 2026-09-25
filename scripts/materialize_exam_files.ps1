param([string]$Root = "D:\project\addmission\all_data")

$ErrorActionPreference = "Stop"
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$downloadLog = [System.Collections.Generic.List[object]]::new()
$failLog = [System.Collections.Generic.List[object]]::new()

$subjectFolders = @{
    "ALEVEL_61" = "A-Level\ALEVEL_61_คณิตศาสตร์ประยุกต์_1"
    "ALEVEL_62" = "A-Level\ALEVEL_62_คณิตศาสตร์ประยุกต์_2"
    "ALEVEL_65" = "A-Level\ALEVEL_65_เคมี"
    "ALEVEL_66" = "A-Level\ALEVEL_66_ชีววิทยา"
    "ALEVEL_70" = "A-Level\ALEVEL_70_สังคมศึกษา"
    "ALEVEL_81" = "A-Level\ALEVEL_81_ภาษาไทย"
    "ALEVEL_82" = "A-Level\ALEVEL_82_ภาษาอังกฤษ"
    "TGAT1_91" = "TGAT\TGAT1_91_การสื่อสารภาษาอังกฤษ"
    "TGAT2_92" = "TGAT\TGAT2_92_การคิดอย่างมีเหตุผล"
    "TGAT3_93" = "TGAT\TGAT3_93_สมรรถนะการทำงาน"
    "TPAT1_10" = "TPAT\TPAT1_10_วิชาเฉพาะ_กสพท"
}

function Safe([string]$s) {
    return (($s -replace '[<>:"/\\|?*]', '_') -replace '\s+', '_').Trim('_')
}

function Ensure([string]$p) {
    if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

function TargetDir([string]$code, [string]$year, [string]$kind="ไฟล์ข้อสอบที่ดาวน์โหลด") {
    $p = Join-Path $Root $subjectFolders[$code]
    $p = Join-Path $p $year
    $p = Join-Path $p $kind
    Ensure $p
    return $p
}

function Detect-Extension([string]$path) {
    $b = [IO.File]::ReadAllBytes($path)
    if ($b.Length -ge 5 -and [Text.Encoding]::ASCII.GetString($b,0,5) -eq '%PDF-') { return '.pdf' }
    if ($b.Length -ge 8 -and $b[0] -eq 0x89 -and [Text.Encoding]::ASCII.GetString($b,1,3) -eq 'PNG') { return '.png' }
    if ($b.Length -ge 3 -and $b[0] -eq 0xFF -and $b[1] -eq 0xD8 -and $b[2] -eq 0xFF) { return '.jpg' }
    if ($b.Length -ge 4 -and [Text.Encoding]::ASCII.GetString($b,0,2) -eq 'PK') { return '.zip' }
    return '.bin'
}

function Download-Drive([string]$code, [string]$year, [string]$name, [string]$id, [string]$sourcePage) {
    $dir = TargetDir $code $year
    $tmp = Join-Path $dir ((Safe $name) + '.download')
    $url = "https://drive.usercontent.google.com/download?id=$id&export=download&confirm=t"
    try {
        Invoke-WebRequest -Uri $url -OutFile $tmp -TimeoutSec 180
        $ext = Detect-Extension $tmp
        if ($ext -eq '.bin') {
            Remove-Item -LiteralPath $tmp -Force
            throw "Google Drive did not return a downloadable document"
        }
        $dest = Join-Path $dir ((Safe $name) + $ext)
        Move-Item -LiteralPath $tmp -Destination $dest -Force
        $downloadLog.Add([pscustomobject]@{exam_code=$code;year=$year;name=$name;file=$dest;source_url="https://drive.google.com/file/d/$id/view";source_page=$sourcePage;method='direct_download'})
    } catch {
        if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force }
        $failLog.Add([pscustomobject]@{exam_code=$code;year=$year;name=$name;source="https://drive.google.com/file/d/$id/view";error=$_.Exception.Message})
    }
}

function Print-Page([string]$code, [string]$year, [string]$name, [string]$url, [string]$kind="ไฟล์ข้อสอบจากหน้าเว็บ") {
    $dir = TargetDir $code $year $kind
    $dest = Join-Path $dir ((Safe $name) + '.pdf')
    $localProfile = Join-Path $Root ("_index\chrome-profile-" + [guid]::NewGuid().ToString('N'))
    try {
        & $chrome --headless --disable-gpu --no-sandbox "--user-data-dir=$localProfile" --no-pdf-header-footer --virtual-time-budget=15000 "--print-to-pdf=$dest" $url 2>$null
        if (-not (Test-Path -LiteralPath $dest)) { throw "Chrome did not create PDF" }
        $ext = Detect-Extension $dest
        if ($ext -ne '.pdf') { throw "Printed output is not PDF" }
        $downloadLog.Add([pscustomobject]@{exam_code=$code;year=$year;name=$name;file=$dest;source_url=$url;source_page=$url;method='print_to_pdf'})
    } catch {
        $failLog.Add([pscustomobject]@{exam_code=$code;year=$year;name=$name;source=$url;error=$_.Exception.Message})
    } finally {
        Start-Sleep -Milliseconds 250
        if(Test-Path -LiteralPath $localProfile){try{Remove-Item -LiteralPath $localProfile -Recurse -Force -ErrorAction Stop}catch{}}
    }
}

# TGAT actual/reconstructed papers and practice sets exposed as downloadable files.
$tgatPage = 'https://dekuni.com/tgat-test/'
$driveFiles = @(
    @{C='TGAT1_91';Y='2569';N='TGAT1 ปี 2569 พร้อมเฉลย';I='1E3yokL3uWemLoiaaLCKCbX21wEA8tN9B'},
    @{C='TGAT2_92';Y='2569';N='TGAT2-3 ปี 2569 ชุดที่ 1';I='1tl4ApTbUJa5MtuYI1zCrgLgBVH8aGDIj'},
    @{C='TGAT3_93';Y='2569';N='TGAT2-3 ปี 2569 ชุดที่ 1';I='1tl4ApTbUJa5MtuYI1zCrgLgBVH8aGDIj'},
    @{C='TGAT2_92';Y='2569';N='TGAT2-3 ปี 2569 เฉลยชุดที่ 1';I='105N7tfobcaIhG9DfHozuL4uwEMa5ToVf'},
    @{C='TGAT3_93';Y='2569';N='TGAT2-3 ปี 2569 เฉลยชุดที่ 1';I='105N7tfobcaIhG9DfHozuL4uwEMa5ToVf'},
    @{C='TGAT2_92';Y='2569';N='TGAT2-3 ปี 2569 ชุดที่ 2 หรือเฉลย';I='1ZLxhT3YX35oDh2A_O8fHDjRd98iaA58H'},
    @{C='TGAT3_93';Y='2569';N='TGAT2-3 ปี 2569 ชุดที่ 2 หรือเฉลย';I='1ZLxhT3YX35oDh2A_O8fHDjRd98iaA58H'},
    @{C='TGAT1_91';Y='2567';N='TGAT1 ปี 2567 พร้อมเฉลย';I='1FTm6qQ9KYHE7FSzl4uGa0LGBH2j2UbpV'},
    @{C='TGAT2_92';Y='2567';N='TGAT2 ปี 2567 พร้อมเฉลย';I='1wuM2h-HWp-IPlrExCxeC3ZC4rhL6R2z5'},
    @{C='TGAT1_91';Y='2566';N='TGAT1 ปี 2566 พร้อมเฉลย';I='16HSRGCag0YDaPGWk_fwH0bV9uKNtDLgq'},
    @{C='TGAT3_93';Y='2566';N='TGAT3 ปี 2566 พร้อมเฉลย';I='1oB_5yME_j3jnosH8UfFr3s1t9SIInPle'},
    @{C='TGAT1_91';Y='ไม่ระบุปี';N='แนวข้อสอบ TGAT ทุกพาร์ต';I='1JVxQESx9EHtrDk5RIrn0FUBN7nf3bS3-'},
    @{C='TGAT2_92';Y='ไม่ระบุปี';N='แนวข้อสอบ TGAT ทุกพาร์ต';I='1JVxQESx9EHtrDk5RIrn0FUBN7nf3bS3-'},
    @{C='TGAT3_93';Y='ไม่ระบุปี';N='แนวข้อสอบ TGAT ทุกพาร์ต';I='1JVxQESx9EHtrDk5RIrn0FUBN7nf3bS3-'},
    @{C='TGAT1_91';Y='ไม่ระบุปี';N='แนวข้อสอบ TGAT ง่ายถึงปานกลาง พร้อมเฉลย';I='1Wmm3nWb_N4lG-qw4VXQmvnxrLEvUOFAV'},
    @{C='TGAT2_92';Y='ไม่ระบุปี';N='แนวข้อสอบ TGAT ง่ายถึงปานกลาง พร้อมเฉลย';I='1Wmm3nWb_N4lG-qw4VXQmvnxrLEvUOFAV'},
    @{C='TGAT3_93';Y='ไม่ระบุปี';N='แนวข้อสอบ TGAT ง่ายถึงปานกลาง พร้อมเฉลย';I='1Wmm3nWb_N4lG-qw4VXQmvnxrLEvUOFAV'},
    @{C='TGAT1_91';Y='ไม่ระบุปี';N='แนวข้อสอบ TGAT ระดับยาก พร้อมเฉลย';I='1SjBmV6uVNcIeznYHuUBojM8fzgoNkZG3'},
    @{C='TGAT2_92';Y='ไม่ระบุปี';N='แนวข้อสอบ TGAT ระดับยาก พร้อมเฉลย';I='1SjBmV6uVNcIeznYHuUBojM8fzgoNkZG3'},
    @{C='TGAT3_93';Y='ไม่ระบุปี';N='แนวข้อสอบ TGAT ระดับยาก พร้อมเฉลย';I='1SjBmV6uVNcIeznYHuUBojM8fzgoNkZG3'},
    @{C='TGAT2_92';Y='ไม่ระบุปี';N='TGAT2 ความสามารถทางภาษา 100 ข้อ';I='1acKLa9XJzBOuG1MwSoy4ztOjShGmi0JD'},
    @{C='TGAT2_92';Y='ไม่ระบุปี';N='TGAT2 ความสามารถทางภาษา 100 ข้อ เฉลย';I='1yvjLjzJ87QDx_UYkchE0z9E3yY0k3hC9'},
    @{C='TGAT2_92';Y='ไม่ระบุปี';N='TGAT2 ความสามารถทางตัวเลข ชุดที่ 2';I='1il9salIuZBKlAll28Gd6H5zw2YY87L5z'},
    @{C='TGAT2_92';Y='ไม่ระบุปี';N='TGAT2 ความสามารถทางตัวเลข ชุดที่ 2 เฉลย';I='1in47XkLzV6oaxC-pgIcfwNLKHL1x5Kv4'}
)
foreach ($f in $driveFiles) { Download-Drive $f.C $f.Y $f.N $f.I $tgatPage }

# TPAT1 ethics files.
$tpatPage='https://dekuni.com/tpat1-etheis/'
Download-Drive 'TPAT1_10' 'ไม่ระบุปี' 'สรุปจริยธรรมทางการแพทย์ ชุดที่ 1' '1IssxYDiSRkpDl2mN8W1x_WDfqzhWFS-7' $tpatPage
Download-Drive 'TPAT1_10' 'ไม่ระบุปี' 'สรุปจริยธรรมทางการแพทย์ ชุดที่ 2' '1TYY7kNRyUkS3M4g-V8Sqthmh__Kp385d' $tpatPage
Download-Drive 'TPAT1_10' 'ไม่ระบุปี' 'รวมข้อสอบ TPAT1 จริยธรรม พร้อมเฉลย' '1kdrAXXyrOFhWfh8KiMmnTSREQnHw7qoT' $tpatPage

# A-Level English / former 9-subject English archive.
$engPage='https://dekuni.com/eng-alevel/'
$eng = @(
    @{Y='2568';N='A-Level อังกฤษ 2568 พร้อมเฉลยละเอียด ชุดที่ 1';I='13NEujwQSKD_4_SZAkUDfX9g1KMFms_rh'},
    @{Y='2568';N='A-Level อังกฤษ 2568 พร้อมเฉลยละเอียด ชุดที่ 2';I='1abUZW7RJs5J0aBE7XpxoYRaSiT1JJzYW'},
    @{Y='2567';N='A-Level อังกฤษ 2567 ข้อสอบ';I='1GTGAZeI77a2dPmHjOoG6EMgEv9ewpkMP'},
    @{Y='2567';N='A-Level อังกฤษ 2567 เฉลยละเอียด';I='1EuQe7yYmLTu5RTPuMviZ6T5VNvK3r-P5'},
    @{Y='2566';N='A-Level อังกฤษ 2566 ข้อสอบ';I='1YL_strFMOH37kyzH__BIbLggyo_M7EYT'},
    @{Y='2565';N='วิชาสามัญอังกฤษ 2565 ข้อสอบ';I='1QGRfTecLDTeqFnLxkmxs1f0x1Gf5Ur9p'},
    @{Y='2565';N='วิชาสามัญอังกฤษ 2565 เฉลย';I='1JhhVO99lS4cBOiibkyBJY5_I9A-FXNIf'},
    @{Y='2564';N='วิชาสามัญอังกฤษ 2564 ข้อสอบ';I='1sIuhYWovudnkxf4zLAvaeVWgyrSAOIn6'},
    @{Y='2564';N='วิชาสามัญอังกฤษ 2564 เฉลย';I='1AJMitXUBduFv1t-k1citD4HW3C6PhDtV'},
    @{Y='2563';N='วิชาสามัญอังกฤษ 2563 ข้อสอบ';I='1paebRQSlsAjNSz_C7o5qiC6N_rMXhiJ4'},
    @{Y='2562';N='วิชาสามัญอังกฤษ 2562 ข้อสอบ';I='1UQZ4q67hzEkwEr2BiUmhefoXf-uUY14Q'},
    @{Y='2561';N='วิชาสามัญอังกฤษ 2561 ข้อสอบ';I='1ybyprPTQ_jEMVAivjqbn5rrDQuTYBDkO'},
    @{Y='2560';N='วิชาสามัญอังกฤษ 2560 ข้อสอบ';I='1XKC991desJT0sCn431pPJMBcQowDB3uq'},
    @{Y='2559';N='วิชาสามัญอังกฤษ 2559 ข้อสอบ';I='1_m6n6aMCODnMqujKrcOKGN-FYIh5gB90'},
    @{Y='2558';N='วิชาสามัญอังกฤษ 2558 ข้อสอบ';I='1O8hzUC-EQW4wh9mvbjwZo4IvqDhzFn4U'},
    @{Y='2558';N='วิชาสามัญอังกฤษ 2558 เฉลย';I='1j7JAMUegur8-jV7G0-2PGNoqEriFWWdc'},
    @{Y='2557';N='วิชาสามัญอังกฤษ 2557 ข้อสอบ';I='1fKP5XLc5zYXo91oPq_f9diszhRXC_oh9'},
    @{Y='2556';N='วิชาสามัญอังกฤษ 2556 ข้อสอบ';I='11Z3ied89KquAdifaZPsyTSh_3uwsuUrq'},
    @{Y='2555';N='วิชาสามัญอังกฤษ 2555 ข้อสอบ';I='1XsiosL0HL5loaHxa9sNyp9Xd7wTlYC2D'}
)
foreach($f in $eng){ Download-Drive 'ALEVEL_82' $f.Y $f.N $f.I $engPage }

# A-Level Mathematics 2, years 2566-2569.
$math2Page='https://www.meddentgat.com/posts/free-mock-exam-math2'
$math2=@(
    @{Y='2566';I='1NJvek61CKAQxTQftStOhybK6bhATlGlm'},
    @{Y='2567';I='1z_w6-lH4tgkzTK_ZesBfgV94R6an2fYf'},
    @{Y='2568';I='1Sfn6mluWf3wVhptWuhseqqgUrGT5FavQ'},
    @{Y='2569';I='1b5-eFT63aM2i9KRtdWISso4l_Dfd4WeT'}
)
foreach($f in $math2){Download-Drive 'ALEVEL_62' $f.Y "A-Level คณิตศาสตร์ประยุกต์ 2 ปี $($f.Y)" $f.I $math2Page}

# A-Level Social Studies full web papers/keys and downloadable detailed solutions.
foreach($y in 2566,2567,2568,2569){
    Print-Page 'ALEVEL_70' "$y" "A-Level สังคมศึกษา $y ข้อสอบจากคลังครูนาย" "https://nine.wr.ac.th/Online-lesson/enter-u/Exam-Archive/soc$($y.ToString().Substring(2))"
}
foreach($y in 2566,2568,2569){
    Print-Page 'ALEVEL_70' "$y" "A-Level สังคมศึกษา $y เฉลยจากคลังครูนาย" "https://nine.wr.ac.th/Online-lesson/enter-u/Exam-Archive/keysoc$($y.ToString().Substring(2))"
}
Download-Drive 'ALEVEL_70' '2569' 'A-Level สังคมศึกษา 2569 เฉลยละเอียด' '15DTo6CR2ISXyesaNnXAzioEwsFlYfaqg' 'https://nine.wr.ac.th/Online-lesson/enter-u/Exam-Archive'
Download-Drive 'ALEVEL_70' '2568' 'A-Level สังคมศึกษา 2568 เฉลยละเอียด' '1wQ96zvVC0LSomt89x5kUdVVoVNQWI1nS' 'https://nine.wr.ac.th/Online-lesson/enter-u/Exam-Archive'
Download-Drive 'ALEVEL_70' '2566' 'A-Level สังคมศึกษา 2566 ข้อสอบสำรอง' '1nTk9dZR8wIrelCBdHvCbv-UR6nvUbDTU' 'https://nine.wr.ac.th/Online-lesson/enter-u/Exam-Archive'
Download-Drive 'ALEVEL_70' '2566' 'A-Level สังคมศึกษา 2566 เฉลย' '1WMbYFOLh-CTAZlKSgXt2ErBvmo5gRYz6' 'https://nine.wr.ac.th/Online-lesson/enter-u/Exam-Archive'

# Other exam pages that publish questions as HTML rather than a direct PDF.
Print-Page 'ALEVEL_61' '2566' 'A-Level คณิตศาสตร์ประยุกต์ 1 ปี 2566' 'https://www.cututoronline.com/%E0%B8%84%E0%B8%A5%E0%B8%B1%E0%B8%87%E0%B8%82%E0%B9%89%E0%B8%AD%E0%B8%AA%E0%B8%AD%E0%B8%9A/%E0%B8%82%E0%B9%89%E0%B8%AD%E0%B8%AA%E0%B8%AD%E0%B8%9Aa-level-%E0%B8%84%E0%B8%93%E0%B8%B4%E0%B8%95%E0%B8%9B%E0%B8%A3%E0%B8%B0%E0%B8%A2%E0%B8%B8%E0%B8%81%E0%B8%95%E0%B9%8C-1-%E0%B8%9B%E0%B8%B52566/'
Print-Page 'ALEVEL_61' '2567' 'A-Level คณิตศาสตร์ประยุกต์ 1 ปี 2567' 'https://www.cututoronline.com/%E0%B8%84%E0%B8%A5%E0%B8%B1%E0%B8%87%E0%B8%82%E0%B9%89%E0%B8%AD%E0%B8%AA%E0%B8%AD%E0%B8%9A/%E0%B8%82%E0%B9%89%E0%B8%AD%E0%B8%AA%E0%B8%AD%E0%B8%9Aa-level-%E0%B8%84%E0%B8%93%E0%B8%B4%E0%B8%95%E0%B8%9B%E0%B8%A3%E0%B8%B0%E0%B8%A2%E0%B8%B8%E0%B8%81%E0%B8%95%E0%B9%8C-1-%E0%B8%9B%E0%B8%B52567/'
Print-Page 'ALEVEL_66' 'รวม_2566-2568' 'คลัง A-Level ชีววิทยาย้อนหลัง' 'https://www.bionont.com/a-level-biology-past-exams'
Print-Page 'ALEVEL_81' 'รวม_2566-2568' 'คลังเฉลย A-Level ภาษาไทยย้อนหลัง' 'https://panyasociety.com/course/16/chapter/493'
Print-Page 'ALEVEL_65' 'รวม_2567-2569' 'คลังเฉลย A-Level เคมีย้อนหลัง' 'https://panyasociety.com/course/91/chapter/9265'

# Turn every remaining URL shortcut into a local PDF, then remove shortcuts and saved HTML pages.
$cacheDir=Join-Path $Root '_index\web-pdf-cache'
Ensure $cacheDir
foreach($shortcut in Get-ChildItem -LiteralPath $Root -Recurse -File -Filter '*.url'){
    $line=Get-Content -LiteralPath $shortcut.FullName | Where-Object {$_ -like 'URL=*'} | Select-Object -First 1
    if(-not $line){continue}
    $url=$line.Substring(4)
    $bytes=[Text.Encoding]::UTF8.GetBytes($url)
    $sha=[Security.Cryptography.SHA256]::Create()
    try{$key=([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').Substring(0,24)}finally{$sha.Dispose()}
    $cached=Join-Path $cacheDir "$key.pdf"
    if(-not (Test-Path -LiteralPath $cached)){
        $shortcutProfile = Join-Path $Root ("_index\chrome-profile-" + [guid]::NewGuid().ToString('N'))
        try{
            & $chrome --headless --disable-gpu --no-sandbox "--user-data-dir=$shortcutProfile" --no-pdf-header-footer --virtual-time-budget=12000 "--print-to-pdf=$cached" $url 2>$null
        }catch{}finally{Start-Sleep -Milliseconds 250; if(Test-Path -LiteralPath $shortcutProfile){try{Remove-Item -LiteralPath $shortcutProfile -Recurse -Force -ErrorAction Stop}catch{}}}
    }
    if(Test-Path -LiteralPath $cached){
        $dest=[IO.Path]::ChangeExtension($shortcut.FullName,'.pdf')
        Copy-Item -LiteralPath $cached -Destination $dest -Force
        Remove-Item -LiteralPath $shortcut.FullName -Force
    }
}

foreach($html in Get-ChildItem -LiteralPath $Root -Recurse -File -Filter '*.html'){
    $candidate=[IO.Path]::ChangeExtension($html.FullName,'.pdf')
    if(-not (Test-Path -LiteralPath $candidate)){
        $match=Import-Csv (Join-Path $Root '_index\manifest.csv') | Where-Object local_path -eq $html.FullName | Select-Object -First 1
        if($match -and $match.source_url){
            $htmlProfile = Join-Path $Root ("_index\chrome-profile-" + [guid]::NewGuid().ToString('N'))
            try{ & $chrome --headless --disable-gpu --no-sandbox "--user-data-dir=$htmlProfile" --no-pdf-header-footer --virtual-time-budget=12000 "--print-to-pdf=$candidate" $match.source_url 2>$null }catch{}finally{Start-Sleep -Milliseconds 250; if(Test-Path -LiteralPath $htmlProfile){try{Remove-Item -LiteralPath $htmlProfile -Recurse -Force -ErrorAction Stop}catch{}}}
        }
    }
    if(Test-Path -LiteralPath $candidate){Remove-Item -LiteralPath $html.FullName -Force}
}

# Clean temporary probes created during discovery.
foreach($temp in @((Join-Path $Root '_test_drive'),(Join-Path $Root '_social69_test.pdf'),(Join-Path $Root '_chrome_profile'))){if(Test-Path -LiteralPath $temp){try{Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction Stop}catch{}}}

$downloadLog | Export-Csv -LiteralPath (Join-Path $Root '_index\actual-files-manifest.csv') -NoTypeInformation -Encoding UTF8
$failLog | Export-Csv -LiteralPath (Join-Path $Root '_index\actual-files-failed.csv') -NoTypeInformation -Encoding UTF8
Write-Output "Actual files created: $($downloadLog.Count)"
Write-Output "Failed: $($failLog.Count)"
