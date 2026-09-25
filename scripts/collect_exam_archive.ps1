param(
    [string]$TargetRoot = "D:\project\addmission\all_data"
)

$ErrorActionPreference = "Stop"
$retrieved = "2026-09-19"

$subjects = @(
    @{ Group="A-Level"; Code="ALEVEL_61"; Name="คณิตศาสตร์ประยุกต์ 1"; Asset="math1"; Blueprint="a-level-61-math1" },
    @{ Group="A-Level"; Code="ALEVEL_62"; Name="คณิตศาสตร์ประยุกต์ 2"; Asset="math2"; Blueprint="a-level-62-math2" },
    @{ Group="A-Level"; Code="ALEVEL_63"; Name="วิทยาศาสตร์ประยุกต์"; Asset="sci"; Blueprint="a-level-63-sci" },
    @{ Group="A-Level"; Code="ALEVEL_64"; Name="ฟิสิกส์"; Asset="phy"; Blueprint="a-level-64-phy" },
    @{ Group="A-Level"; Code="ALEVEL_65"; Name="เคมี"; Asset="chem"; Blueprint="a-level-65-chem" },
    @{ Group="A-Level"; Code="ALEVEL_66"; Name="ชีววิทยา"; Asset="bio"; Blueprint="a-level-66-bio" },
    @{ Group="A-Level"; Code="ALEVEL_70"; Name="สังคมศึกษา"; Asset="soc"; Blueprint="a-level-70-soc" },
    @{ Group="A-Level"; Code="ALEVEL_81"; Name="ภาษาไทย"; Asset="thai"; Blueprint="a-level-81-thai" },
    @{ Group="A-Level"; Code="ALEVEL_82"; Name="ภาษาอังกฤษ"; Asset="eng"; Blueprint="a-level-82-eng" },
    @{ Group="A-Level"; Code="ALEVEL_83"; Name="ภาษาฝรั่งเศส"; Asset="fra"; Blueprint="a-level-83-fra" },
    @{ Group="A-Level"; Code="ALEVEL_84"; Name="ภาษาเยอรมัน"; Asset="deu"; Blueprint="a-level-84-deu" },
    @{ Group="A-Level"; Code="ALEVEL_85"; Name="ภาษาญี่ปุ่น"; Asset="jpn"; Blueprint="a-level-85-jpn" },
    @{ Group="A-Level"; Code="ALEVEL_86"; Name="ภาษาเกาหลี"; Asset="kor"; Blueprint="a-level-86-kor" },
    @{ Group="A-Level"; Code="ALEVEL_87"; Name="ภาษาจีน"; Asset="chn"; Blueprint="a-level-87-chn" },
    @{ Group="A-Level"; Code="ALEVEL_88"; Name="ภาษาบาลี"; Asset="bal"; Blueprint="a-level-88-bal" },
    @{ Group="A-Level"; Code="ALEVEL_89"; Name="ภาษาสเปน"; Asset="esp"; Blueprint="a-level-89-esp" },
    @{ Group="TGAT"; Code="TGAT1_91"; Name="การสื่อสารภาษาอังกฤษ"; Blueprint="tgat1-91" },
    @{ Group="TGAT"; Code="TGAT2_92"; Name="การคิดอย่างมีเหตุผล"; Blueprint="tgat2-92" },
    @{ Group="TGAT"; Code="TGAT3_93"; Name="สมรรถนะการทำงาน"; Blueprint="tgat3-93" },
    @{ Group="TPAT"; Code="TPAT1_10"; Name="วิชาเฉพาะ กสพท"; Blueprint=$null },
    @{ Group="TPAT"; Code="TPAT2_20"; Name="ความถนัดศิลปกรรมศาสตร์"; Blueprint="tpat2-20" },
    @{ Group="TPAT"; Code="TPAT3_30"; Name="ความถนัดวิทยาศาสตร์ เทคโนโลยี และวิศวกรรมศาสตร์"; Blueprint="tpat3-30" },
    @{ Group="TPAT"; Code="TPAT4_40"; Name="ความถนัดสถาปัตยกรรมศาสตร์"; Blueprint="tpat4-40" },
    @{ Group="TPAT"; Code="TPAT5_50"; Name="ความถนัดครุศาสตร์-ศึกษาศาสตร์"; Blueprint="tpat5-50" }
)

$manifest = [System.Collections.Generic.List[object]]::new()
$failures = [System.Collections.Generic.List[object]]::new()

function Safe-Name([string]$value) {
    return ($value -replace '[<>:"/\\|?*]', '_' -replace '\s+', '_')
}

function Subject-Root($subject) {
    $folder = "{0}_{1}" -f $subject.Code, (Safe-Name $subject.Name)
    return Join-Path (Join-Path $TargetRoot $subject.Group) $folder
}

function Ensure-Folder([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

function Add-UrlFile([string]$path, [string]$url) {
    Ensure-Folder (Split-Path -Parent $path)
    Set-Content -LiteralPath $path -Encoding UTF8 -Value "[InternetShortcut]`r`nURL=$url`r`n"
}

function Add-ManifestRow($subject, [int]$year, [string]$kind, [string]$status, [string]$visibility, [string]$url, [string]$localPath, [string]$note) {
    $hash = $null
    $size = $null
    if ($localPath -and (Test-Path -LiteralPath $localPath)) {
        $file = Get-Item -LiteralPath $localPath
        $size = $file.Length
        if ($file.Extension -ne ".url") {
            $hash = (Get-FileHash -LiteralPath $localPath -Algorithm SHA256).Hash
        }
    }
    $manifest.Add([pscustomobject]@{
        group=$subject.Group; exam_code=$subject.Code; subject=$subject.Name; year=$year
        material_type=$kind; license_status=$status; visibility=$visibility
        source_url=$url; retrieved_date=$retrieved; local_path=$localPath
        bytes=$size; sha256=$hash; note=$note
    })
}

function Download-File($subject, [int]$year, [string]$kind, [string]$url, [string]$path, [string]$status="official_public", [string]$visibility="public", [string]$note="") {
    Ensure-Folder (Split-Path -Parent $path)
    try {
        Invoke-WebRequest -Uri $url -OutFile $path -TimeoutSec 120
        Add-ManifestRow $subject $year $kind $status $visibility $url $path $note
    } catch {
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
        $failures.Add([pscustomobject]@{ exam_code=$subject.Code; year=$year; url=$url; error=$_.Exception.Message })
    }
}

Ensure-Folder $TargetRoot
Ensure-Folder (Join-Path $TargetRoot "_index")
Ensure-Folder (Join-Path $TargetRoot "_shared")

# Official A-Level 2568 full papers (the PDFs also contain the official answer section).
foreach ($subject in ($subjects | Where-Object Group -eq "A-Level")) {
    $root = Subject-Root $subject
    $paperDir = Join-Path $root "2568\ข้อสอบจริง_ทางการ"
    $paperUrl = "https://assets.mytcas.com/68/answer/tcas68-{0}-a-level.pdf" -f $subject.Asset
    $paperPath = Join-Path $paperDir ("{0}_2568_ข้อสอบพร้อมเฉลยทางการ.pdf" -f $subject.Code)
    Download-File $subject 2568 "ข้อสอบจริงพร้อมเฉลย" $paperUrl $paperPath
}

# Official combined answer keys. Download once, then place a copy in every subject/year folder.
$shared68 = Join-Path $TargetRoot "_shared\A-Level_2568_เฉลยรวมทางการ.pdf"
$shared69 = Join-Path $TargetRoot "_shared\A-Level_2569_เฉลยรวมทางการ.pdf"
$dummy = $subjects | Where-Object Code -eq "ALEVEL_61" | Select-Object -First 1
Download-File $dummy 2568 "เฉลยรวม" "https://assets.mytcas.com/68/alevel/alevel-answers.pdf" $shared68
Download-File $dummy 2569 "เฉลยรวม" "https://assets.mytcas.com/69/alevel/69_answers_61-89.pdf" $shared69

foreach ($subject in ($subjects | Where-Object Group -eq "A-Level")) {
    foreach ($year in 2568,2569) {
        $source = if ($year -eq 2568) { $shared68 } else { $shared69 }
        $url = if ($year -eq 2568) { "https://assets.mytcas.com/68/alevel/alevel-answers.pdf" } else { "https://assets.mytcas.com/69/alevel/69_answers_61-89.pdf" }
        if (Test-Path -LiteralPath $source) {
            $dest = Join-Path (Subject-Root $subject) "$year\เฉลยทางการ\A-Level_${year}_เฉลยรวมทุกวิชา.pdf"
            Ensure-Folder (Split-Path -Parent $dest)
            Copy-Item -LiteralPath $source -Destination $dest -Force
            Add-ManifestRow $subject $year "เฉลยทางการ" "official_public" "public" $url $dest "ไฟล์รวมทุกวิชา; เก็บสำเนาไว้ในโฟลเดอร์รายวิชาเพื่อค้นง่าย"
        }
    }
}

# Current official TCAS70 blueprints and sample questions.
foreach ($subject in ($subjects | Where-Object { $_.Blueprint })) {
    $url = "https://www.mytcas.com/blueprint/{0}/" -f $subject.Blueprint
    $folder = Join-Path (Subject-Root $subject) "2570\ตัวอย่างข้อสอบ_ทางการ"
    $html = Join-Path $folder ("{0}_2570_blueprint_and_samples.html" -f $subject.Code)
    Download-File $subject 2570 "โครงสร้างและตัวอย่างข้อสอบ" $url $html
    $shortcut = Join-Path $folder "เปิดหน้าต้นฉบับ_MyTCAS.url"
    Add-UrlFile $shortcut $url
    Add-ManifestRow $subject 2570 "ลิงก์หน้าต้นฉบับ" "official_public" "public" $url $shortcut "หน้าออนไลน์อาจแสดงรูปประกอบสมบูรณ์กว่าไฟล์ HTML"
}

# Official TCAS66 user manuals include answer-sheet examples for all exam families.
$manuals = @(
    @{ Group="A-Level"; Url="https://assets.mytcas.com/66/TCAS66-Doc-A-Level.pdf"; File="TCAS66_คู่มือสมัครสอบ_A-Level_และตัวอย่างกระดาษคำตอบ.pdf" },
    @{ Group="TGAT"; Url="https://assets.mytcas.com/66/TCAS66-Doc-TGAT-TPAT.pdf"; File="TCAS66_คู่มือสมัครสอบ_TGAT-TPAT_และตัวอย่างกระดาษคำตอบ.pdf" },
    @{ Group="TPAT"; Url="https://assets.mytcas.com/66/TCAS66-Doc-TGAT-TPAT.pdf"; File="TCAS66_คู่มือสมัครสอบ_TGAT-TPAT_และตัวอย่างกระดาษคำตอบ.pdf" }
)
foreach ($m in $manuals) {
    $groupDir = Join-Path $TargetRoot "$($m.Group)\_เอกสารรวม\2566"
    $path = Join-Path $groupDir $m.File
    $representative = $subjects | Where-Object Group -eq $m.Group | Select-Object -First 1
    Download-File $representative 2566 "คู่มือและตัวอย่างกระดาษคำตอบ" $m.Url $path
}

# Community indexes. Preserve as source links only because redistribution rights for the files they link to are unclear.
$community = @(
    @{ Group="TGAT"; Codes=@("TGAT1_91","TGAT2_92","TGAT3_93"); Years=@(2566,2567,2568,2569); Label="รวมข้อสอบ TGAT ทุกพาร์ต 2566-2569 (ชุมชน)"; Url="https://dekuni.com/tgat-test/" },
    @{ Group="A-Level"; Codes=@("ALEVEL_61","ALEVEL_62","ALEVEL_63","ALEVEL_64","ALEVEL_65","ALEVEL_66","ALEVEL_70","ALEVEL_81","ALEVEL_82","ALEVEL_83","ALEVEL_84","ALEVEL_85","ALEVEL_86","ALEVEL_87","ALEVEL_88","ALEVEL_89"); Years=@(2566,2567,2568,2569); Label="คลังข้อสอบเข้ามหาวิทยาลัยย้อนหลัง (ชุมชน)"; Url="https://nine.wr.ac.th/Online-lesson/enter-u/Exam-Archive" },
    @{ Group="A-Level"; Codes=@("ALEVEL_62"); Years=@(2566,2567,2568,2569); Label="คณิตศาสตร์ประยุกต์ 2 ปี 2566-2569"; Url="https://www.meddentgat.com/posts/free-mock-exam-math2" },
    @{ Group="A-Level"; Codes=@("ALEVEL_61"); Years=@(2566,2567); Label="คณิตศาสตร์ประยุกต์ 1 ข้อสอบออนไลน์ย้อนหลัง"; Url="https://www.cututoronline.com/%E0%B8%84%E0%B8%A5%E0%B8%B1%E0%B8%87%E0%B8%82%E0%B9%89%E0%B8%AD%E0%B8%AA%E0%B8%AD%E0%B8%9A?type=alevel%E0%B8%84%E0%B8%93%E0%B8%B4%E0%B8%95%E0%B8%A8%E0%B8%B2%E0%B8%AA%E0%B8%95%E0%B8%A3%E0%B9%8C%E0%B8%9B%E0%B8%A3%E0%B8%B0%E0%B8%A2%E0%B8%B8%E0%B8%81%E0%B8%95%E0%B9%8C1" },
    @{ Group="A-Level"; Codes=@("ALEVEL_66"); Years=@(2566,2567,2568); Label="ชีววิทยา A-Level ย้อนหลัง"; Url="https://www.bionont.com/a-level-biology-past-exams" },
    @{ Group="A-Level"; Codes=@("ALEVEL_65"); Years=@(2567,2568,2569); Label="เคมี A-Level เฉลยย้อนหลัง"; Url="https://panyasociety.com/course/91/chapter/9265" },
    @{ Group="A-Level"; Codes=@("ALEVEL_81"); Years=@(2566,2567,2568); Label="ภาษาไทย A-Level เฉลยย้อนหลัง"; Url="https://panyasociety.com/course/16/chapter/493" },
    @{ Group="A-Level"; Codes=@("ALEVEL_82"); Years=@(2566,2567,2568); Label="ภาษาอังกฤษ A-Level และ 9 วิชาสามัญย้อนหลัง"; Url="https://dekuni.com/eng-alevel/" },
    @{ Group="TPAT"; Codes=@("TPAT1_10"); Years=@(2570); Label="TPAT1 ตัวอย่างพาร์ตเชาวน์ปัญญา"; Url="https://www.smartmathpro.com/article/mathtpat1/" },
    @{ Group="TPAT"; Codes=@("TPAT1_10"); Years=@(2570); Label="TPAT1 ตัวอย่างพาร์ตจริยธรรม"; Url="https://www.smartmathpro.com/article/tpat1-medical-ethics/" },
    @{ Group="TPAT"; Codes=@("TPAT1_10"); Years=@(2570); Label="TPAT1 ตัวอย่างพาร์ตเชื่อมโยง"; Url="https://www.smartmathpro.com/article/tpat1-connecting-thinking-test/" },
    @{ Group="TPAT"; Codes=@("TPAT1_10"); Years=@(2566,2567,2568,2569); Label="TPAT1 จริยธรรมย้อนหลัง 10 ปี (ชุมชน)"; Url="https://dekuni.com/tpat1-etheis/" }
)
foreach ($entry in $community) {
    foreach ($code in $entry.Codes) {
        $subject = $subjects | Where-Object Code -eq $code | Select-Object -First 1
        foreach ($year in $entry.Years) {
            $folder = Join-Path (Subject-Root $subject) "$year\แหล่งข้อมูลชุมชน_ตรวจสิทธิ์ก่อนใช้"
            $path = Join-Path $folder ((Safe-Name $entry.Label) + ".url")
            Add-UrlFile $path $entry.Url
            Add-ManifestRow $subject $year "ลิงก์คลังชุมชน" "unknown" "internal_only" $entry.Url $path "ไม่ได้ดาวน์โหลดไฟล์ที่เชื่อมโยงต่อ เพราะยังยืนยันสิทธิ์เผยแพร่ซ้ำไม่ได้"
        }
    }
}

# Explain years for which the official full paper was not found.
foreach ($subject in $subjects) {
    $years = if ($subject.Group -eq "A-Level") { @(2566,2567,2569) } else { @(2566,2567,2568,2569) }
    foreach ($year in $years) {
        $folder = Join-Path (Subject-Root $subject) "$year"
        Ensure-Folder $folder
        $notice = Join-Path $folder "สถานะไฟล์ทางการ.txt"
        if (-not (Test-Path -LiteralPath $notice)) {
            $text = @"
ยังไม่พบไฟล์ข้อสอบจริงฉบับเต็มที่หน่วยงานเจ้าของข้อสอบเปิดให้ดาวน์โหลดอย่างเป็นทางการสำหรับวิชา $($subject.Code) $($subject.Name) ปี $year ณ วันที่ $retrieved

โปรดดูโฟลเดอร์เฉลยทางการ ตัวอย่างข้อสอบทางการ หรือแหล่งข้อมูลชุมชนที่อยู่ในปีนี้แทน
ไฟล์จากแหล่งชุมชนต้องตรวจสิทธิ์และเทียบต้นฉบับก่อนนำไปเผยแพร่ต่อ
"@
            Set-Content -LiteralPath $notice -Encoding UTF8 -Value $text
        }
    }
}

$manifestPath = Join-Path $TargetRoot "_index\manifest.csv"
$manifest | Sort-Object group,exam_code,year,material_type,local_path | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8
$failurePath = Join-Path $TargetRoot "_index\failed-downloads.csv"
$failures | Export-Csv -LiteralPath $failurePath -NoTypeInformation -Encoding UTF8

$readme = @'
# คลังข้อสอบ TGAT / TPAT / A-Level

รวบรวมเมื่อ {{RETRIEVED}} และแบ่งตาม `หมวดสอบ / วิชา / ปี / ประเภทเอกสาร`

- `ข้อสอบจริง_ทางการ` คือไฟล์ที่ดาวน์โหลดจากเว็บไซต์ MyTCAS โดยตรง
- `เฉลยทางการ` คือเฉลยที่ประกาศโดย MyTCAS
- `ตัวอย่างข้อสอบ_ทางการ` คือ Blueprint และตัวอย่าง ไม่ใช่ข้อสอบจริงทั้งชุด
- `แหล่งข้อมูลชุมชน_ตรวจสิทธิ์ก่อนใช้` เก็บเพียงลิงก์ เพราะสิทธิ์ในการนำไฟล์เหล่านั้นมาเผยแพร่ซ้ำยังไม่ชัดเจน
- `manifest.csv` บันทึก URL ต้นทาง วันที่ดึงไฟล์ ขนาด และ SHA-256 เพื่อใช้ตรวจสอบย้อนหลัง

## ขอบเขตที่พบ

- A-Level ปี 2568: ข้อสอบจริงพร้อมเฉลยทางการครบ 16 วิชา
- A-Level ปี 2569: พบเฉลยทางการครบ 16 วิชา แต่ยังไม่พบข้อสอบจริงเต็มชุดจากทางการ
- TGAT และ TPAT2-5: พบ Blueprint/ตัวอย่างข้อสอบทางการของ TCAS70
- TPAT1: ดูแลโดย กสพท.; ไม่พบข้อสอบจริงเต็มชุดที่เปิดดาวน์โหลดจากทางการ จึงเก็บลิงก์ตัวอย่างแยกพาร์ตไว้เท่านั้น
- ปี 2566-2567: พบคู่มือสอบทางการและแหล่งชุมชนบางส่วน แต่ไม่พบคลังข้อสอบจริงเต็มชุดอย่างเป็นทางการจาก MyTCAS

รายละเอียดทุกไฟล์อยู่ที่ `_index/manifest.csv`; รายการดาวน์โหลดที่ล้มเหลวอยู่ที่ `_index/failed-downloads.csv`
'@
$readme = $readme.Replace("{{RETRIEVED}}", $retrieved)
Set-Content -LiteralPath (Join-Path $TargetRoot "README.md") -Encoding UTF8 -Value $readme

Write-Output ("Archive root: {0}" -f $TargetRoot)
Write-Output ("Manifest rows: {0}" -f $manifest.Count)
Write-Output ("Download failures: {0}" -f $failures.Count)
