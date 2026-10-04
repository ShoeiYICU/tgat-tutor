# ตรวจไขว้ TGAT1 — Claude ตรวจงานที่ Codex เขียน

ตรวจไฟล์ `data/problems/tgat1.*.json` แบบอ่านอย่างเดียวครบ 35 หัวข้อ 280 ข้อ โดยไม่ได้แก้ไฟล์ของ Codex
**Codex เป็นผู้ตัดสินว่ารับหรือไม่รับ** ตามกติกาเดียวกับรอบก่อน

**ขอบเขตที่ตรวจ:** โจทย์ ตัวเลือก และคำตอบที่ทำเครื่องหมายไว้ทุกข้อ · ข้อที่อิงบทอ่านเทียบกับบทอ่านฉบับเต็มทั้ง 6 เรื่อง
**ที่ไม่ได้ตรวจละเอียด:** คำใบ้ วิธีคิดทีละขั้น และคำอธิบายเฉลยภาษาไทย

## ภาพรวม

คุณภาพดี ข้อที่อิงบทอ่าน (40 ข้อ) คำตอบตรงกับบทอ่านทุกข้อ ข้อไวยากรณ์และคำถามย้อนกลับถูกต้อง
ข้อ 0001–0006 ของหัวข้อบทสนทนาใช้ตัวลวงที่ดีมาก คือผิดด้วยเหตุผลทางการสื่อสารจริง
(ตอบผิดหน้าที่ ผิดระดับภาษา ตอบคำถามอื่น) ซึ่งตรงกับที่ข้อสอบจริงวัด

## รายการที่พบ

| id ข้อ | ระดับ | ปัญหาที่พบ | ข้อเสนอแก้ |
|---|---|---|---|
| prob.tgat1.reading.comprehension.specific_detail.0008 | **ต้องแก้** | มีคำตอบถูกสองข้อ โจทย์ถามว่าใครทำงานทางไกลในวันพฤหัสไม่ได้ คำตอบคือเสมียนที่จ้างมาสามเดือนและต้องดูแลแฟ้ม แต่ตัวลวง "A records clerk hired yesterday" ก็ทำงานทางไกลไม่ได้เช่นกัน เพราะนโยบายบอกว่าพนักงานใหม่ขอได้หลังครบ 60 วัน | เปลี่ยนตัวลวงนี้เป็นคนที่ทำงานทางไกลได้ชัดเจน เช่น "A designer hired four months ago" หรือเปลี่ยนคำถามเป็น "…cannot work remotely **because of the records rule**" |
| prob.tgat1.reading.text_completion.collocation.0007 | **ต้องแก้** | "The committee will ______ a decision" คำตอบคือ make แต่ตัวลวง **take** ใช้ได้จริงในภาษาอังกฤษแบบบริติช (take a decision) ปัญหาเดียวกับที่เคยแก้ในข้อ 0001 ของหัวข้อนี้เมื่อรอบแรก แต่กลับมาอีกในข้อที่เพิ่มทีหลัง | เปลี่ยน take เป็นคำที่ผิดในทุกสำเนียง เช่น give หรือ put |
| prob.tgat1.reading.text_completion.tense_consistency.0008 | ควรแก้ | "The archive ______ to the public since 2019, but it closed for repairs last month." คำตอบ has been open แปลว่ายังเปิดอยู่ถึงตอนนี้ ขัดกับครึ่งหลังที่บอกว่าปิดไปแล้ว ประโยคที่ถูกต้องตามความหมายควรเป็น had been open | เปลี่ยนครึ่งหลังให้ไม่ขัด เช่น "…since 2019, and it now receives over 500 visitors a week." หรือเปลี่ยนคำตอบเป็น had been open พร้อมแก้ประโยคเป็น "…before it closed for repairs last month" |
| prob.tgat1.speaking.long_conversation.discourse_marker.0006 | ควรแก้ | คำตอบคือ Speaking of which แต่ตัวลวง **Actually** ก็ใช้ได้เป็นธรรมชาติ ("That sounds fun! Actually, I just bought a new picnic basket.") เพราะ actually ใช้นำข้อมูลใหม่ที่เกี่ยวข้องได้ | เปลี่ยน Actually เป็น However หรือ Instead ซึ่งขัดกับความต่อเนื่องของประโยคชัดเจน |
| ข้อ 0007–0008 ของหัวข้อบทสนทนา ราว 25 ข้อใน 14 หัวข้อ (รายการด้านล่าง) | ควรแก้ | **ปัญหาเชิงระบบ** ตัวลวงเป็นประโยคที่ไม่มีความหมาย ผู้สอบตัดทิ้งได้โดยไม่ต้องเข้าใจบทสนทนาเลย เช่น "The museum stops art." · "Yes, your bag has two eyes." · "The train announced you." · "The shirt exchanged me." · "Friday wants to join us." ต่างจากข้อ 0001–0006 ที่ตัวลวงเป็นประโยคถูกไวยากรณ์แต่ผิดหน้าที่ทางการสื่อสาร ข้อกลุ่มนี้จึงง่ายกว่าระดับความยากที่ระบุไว้มาก | เขียนตัวลวงใหม่ให้เป็นประโยคที่พูดได้จริงแต่ไม่เข้ากับบทสนทนา แบบเดียวกับข้อ 0001–0006 เช่น ตอบคำถามผิดชนิด ตอบรับทั้งที่ควรปฏิเสธ ใช้ระดับภาษาผิด หรือตอบสิ่งที่ขัดกับประโยคถัดไป |
| prob.tgat1.reading.foundation.time_management.0003 และ skim_scan.0004 | ข้อสังเกต | เฉลยระบุกลยุทธ์เป็นข้อเท็จจริง ("ทำข้อรายละเอียดก่อน" · "อ่านคำถามก่อนเสมอ") ทั้งที่เป็นคำแนะนำซึ่งผู้สอนแต่ละคนเห็นต่างกันได้ | ถ้าคำอธิบายเฉลยยังไม่ได้เขียนว่าเป็น "วิธีที่แนะนำในบทเรียนนี้" ให้เพิ่ม เพื่อไม่ให้ดูเป็นกฎตายตัว |

### ข้อที่ตัวลวงเป็นประโยคไร้ความหมาย

ตัวอย่างตัวลวงที่พบในแต่ละหัวข้อ (ทั้งหมดอยู่ในข้อ 0007 หรือ 0008)

| หัวข้อ | ตัวอย่างตัวลวง |
|---|---|
| question_response.apology_thanks | I'm sorry to hear your coffee. · Never mind; the figures thanked me. |
| question_response.greeting_intro | The pleasure was yesterday. · No, I don't catch anything. |
| question_response.invitation | Friday wants to join us. · The game is having a night. |
| question_response.opinion_agreement | Neither is the practice. · Yes, time includes workshops. |
| question_response.request_offer_permission | Yes, your bag has two eyes. · The shelf has already moved. |
| question_response.yesno_and_tag | Yes, the form isn't a signature. · The final file did, didn't it? |
| short_conversation.directions_transport | The museum stops art. · The train announced you. |
| short_conversation.phone_appointment | Did Sam speak? · The time moved itself. |
| short_conversation.school_campus | The chemistry opens it. · Why did registration miss you? |
| short_conversation.service_encounter | The shirt exchanged me. · The noise checked out. |
| short_conversation.turn_taking | Did Monday move it? · The data took my notes. |
| long_conversation.problem_solution | The tables should dry the room. · The report should connect. |
| foundation.politeness_level / long_conversation.register_formality | Can the camera borrow me? · I accuse these totals. |

หัวข้อ `wh_question_matching`, `tracking_speakers`, `implied_meaning` และ `discourse_marker` ข้อ 0007–0008 **ไม่มีปัญหานี้**
ตัวลวงเป็นคำตอบของคำถามชนิดอื่นหรือข้อสรุปที่ผิด ซึ่งดีแล้ว ใช้เป็นแบบอย่างได้

## สรุปจำนวน

- ต้องแก้: 2 ข้อ
- ควรแก้: 2 ข้อ + ปัญหาเชิงระบบ 1 เรื่อง (ราว 25 ข้อ)
- ข้อสังเกต: 1 รายการ (2 ข้อ)
- หัวข้อที่ไม่พบปัญหา: 15 จาก 35 หัวข้อ
