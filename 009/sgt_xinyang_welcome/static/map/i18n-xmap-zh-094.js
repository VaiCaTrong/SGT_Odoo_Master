/* Xinyang Report Dashboard — 中文（简体）界面词典 Tiếng Việt → 中文 (v4.11.0)
 * Nạp TRƯỚC i18n.js. Khoá = chuỗi tiếng Việt gốc (giống DICT tiếng Anh trong i18n.js).
 * Chữ chưa có ở đây sẽ tự dùng bản tiếng Anh (không hiện tiếng Việt). Kiểm tra: XINYANG_I18N.missing("zh")
 * Thuật ngữ giữ nguyên: Match Making, MM, KPI, Odoo, GB Submit, Pipeline/stage do Odoo đặt tên, x_address…
 */
(() => {
"use strict";
const DICT = {
  // Đăng nhập
  "Đăng nhập bằng tài khoản Odoo Xinyang. Số liệu GB Submit được đọc từ SGT Odoo bằng cùng tài khoản; quyền xem vẫn do Odoo kiểm soát.":
    "请使用 Xinyang Odoo 账号登录。GB Submit 数据使用同一账号从 SGT Odoo 读取；查看权限仍由 Odoo 控制。",
  "Tài khoản Odoo": "Odoo 账号", "Mật khẩu": "密码", "Đăng nhập": "登录", "Đang đăng nhập...": "正在登录...",
  "dữ liệu giả": "模拟数据", "Vui lòng đăng nhập bằng tài khoản Odoo Xinyang.": "请使用 Xinyang Odoo 账号登录。",
  "Vui lòng nhập đầy đủ tài khoản và mật khẩu Odoo.": "请完整填写 Odoo 账号和密码。",
  // Sidebar & topbar
  "ĐI NHANH": "快速跳转", "BẢN ĐỒ": "地图", "Tổng quan KPI": "KPI 总览", "Dữ liệu & làm mới": "数据与刷新",
  "Chú giải KPI": "KPI 说明", "Bản đồ khách hàng": "客户地图", "Chưa tải dữ liệu": "尚未加载数据",
  "Bài đăng group": "群组帖子", "Data 4 kho": "4 个管道数据", "Tuỳ chỉnh": "自定义", "Làm mới": "刷新",
  "Xuất CSV": "导出 CSV", "Đăng xuất": "退出登录", "Logout": "退出登录",
  "Trạng thái kết nối Odoo và payload gần nhất": "Odoo 连接状态和最近一次数据",
  "Định nghĩa và cách tính từng chỉ số": "各项指标的定义和计算方法",
  "Heatmap & vị trí deal theo x_address": "按 x_address 显示热力图和商机位置",
  // Bộ lọc kỳ
  "Xem theo": "查看方式", "Tuần": "周", "Tháng": "月", "Năm": "年", "Kỳ đang xem": "当前周期",
  "Kỳ trước": "上一周期", "Kỳ sau": "下一周期", "Chọn 1 ngày bất kỳ trong kỳ": "选择周期内任意一天",
  "Kỳ hiện tại": "本周期", "Số kỳ so sánh trên biểu đồ": "图表对比周期数", "(cùng số ngày)": "（相同天数）",
  "Đang đọc dữ liệu Odoo...": "正在读取 Odoo 数据...", "kỳ trước": "上一周期", "Trước": "之前", "cả": "整个周期",
  // Trang dữ liệu
  "Lần tải gần nhất": "最近加载", "Trạng thái dữ liệu": "数据状态", "Payload lần tải gần nhất": "最近一次加载的数据",
  "Đọc lại từ Odoo": "从 Odoo 重新读取", "Bản đồ khách hàng Xinyang": "Xinyang 客户地图", "Tắt": "关闭",
  "đã kết nối": "已连接", "chưa kết nối": "未连接", "tổng": "合计",
  // Drawer tuỳ chỉnh
  "Tuỳ chỉnh dashboard": "自定义仪表板",
  "Chọn biểu đồ hiển thị, loại biểu đồ và độ rộng. Lưu trên trình duyệt này.": "选择要显示的图表、图表类型和宽度。保存在此浏览器中。",
  "Khôi phục mặc định": "恢复默认", "Xong": "完成", "Thẻ KPI": "KPI 卡片", "Hiện tất cả": "全部显示", "Biểu đồ": "图表",
  "Lên": "上移", "Xuống": "下移", "Nửa hàng": "半宽", "Cả hàng": "全宽", "Tải dữ liệu trước khi tuỳ chỉnh.": "请先加载数据再自定义。",
  // Loại biểu đồ & công cụ
  "Bảng xếp hạng": "排行榜", "Cột": "柱状图", "Cột chồng": "堆叠柱状图", "Đường": "折线图", "Vùng": "面积图",
  "Thanh ngang": "条形图", "Thanh ngang chồng": "堆叠条形图", "Tròn": "饼图", "Donut": "环形图", "Bảng": "表格",
  "Ẩn thẻ này": "隐藏此卡片", "hiện lại": "重新显示", "Đưa nhóm này lên trên": "将此分组上移",
  "Đưa nhóm này xuống dưới": "将此分组下移", "Đưa biểu đồ lên trước": "将图表上移", "Đưa biểu đồ xuống sau": "将图表下移",
  "Loại biểu đồ": "图表类型", "Đổi độ rộng": "更改宽度", "Ẩn biểu đồ": "隐藏图表",
  "Chưa có MM nào trong các kỳ này": "这些周期内暂无 MM", "Chưa có dữ liệu trong kỳ này": "本周期暂无数据",
  "Chưa có dữ liệu": "暂无数据", "TỔNG": "合计", "Tổng": "合计", "Nhân sự": "人员", "Kỳ": "周期", "Mục": "项目",
  "Đang tồn ở 4 kho": "仍在 4 个管道中", "Chưa có kho nào": "暂无管道",
  "Data tạo mới trong 4 kho": "4 个管道新建数据", "Data tạo mới trong 4 kho theo kỳ": "各周期 4 个管道新建数据",
  "Data tạo mới mỗi ngày": "每日新建数据", "Mỗi cột = 1 ngày": "每列 = 1 天", "mỗi màu = 1 kho": "每种颜色 = 1 个管道",
  "Trung bình / ngày": "日均",
  "Báo cáo ngày": "日报", "Data trong ngày": "当日数据", "Deal tạo mới ở 4 kho": "4 个管道新建商机",
  "Deal tiến vào stage trong ngày": "当日推进到各阶段的商机", "Bài post FB": "FB 帖子", "Bài đăng group Facebook (GB Submit)": "Facebook 群组帖子（GB Submit）",
  "Tổng bài đăng": "帖子总数", "Content nộp cho project XINYANG": "提交给 XINYANG 项目的内容", "Chưa duyệt": "未审核",
  "Mở dashboard đầy đủ": "打开完整仪表板", "Ngày trước": "前一天", "Ngày sau": "后一天", "Chọn ngày": "选择日期",
  "Dùng tài khoản Odoo Xinyang.": "使用 Xinyang Odoo 账号。", "Đăng nhập thất bại.": "登录失败。", "Không kết nối được máy chủ.": "无法连接服务器。",
  "Không đọc được dữ liệu kho": "无法读取管道数据", "Không đọc được Match Making": "无法读取 Match Making",
  "Không đọc được bài đăng": "无法读取帖子", "Không đọc được content": "无法读取内容", "Chưa kết nối SGT Odoo": "未连接 SGT Odoo",
  "Báo cáo ngày (mobile)": "日报（手机版）",
  "Nhận xét": "评论",
  "Nhập nhận xét trong ngày (tự lưu, có trong ảnh xuất)": "输入当日评论（自动保存，导出图片时包含）",
  "Đang lưu…": "正在保存…",
  "Đã lưu": "已保存",
  "Không lưu được trên trình duyệt này": "无法在此浏览器保存",
  "Chỉ số trong ngày": "当日指标",
  "Data mới": "新数据",
  "vào stage": "进入阶段",
  "Tổng data mới (4 kho)": "新数据合计（4 个管道）",
  "Tổng data mới": "新数据合计",
  "4 kho → MM": "4 个管道 → MM",
  "Tổng bài": "帖子总数",
  "Không đạt": "未通过",
  "Content chưa duyệt": "未审核内容",
  "Content đã duyệt, chưa đăng": "已审核未发布内容",
  "Content đã dùng để đăng": "已用于发布的内容",
  "Đã duyệt": "已审核",
  "Đã dùng": "已使用",
  "Data & Match Making": "数据与 Match Making",
  "Bài đăng & Content": "帖子与内容",
  "+ Chỉ số": "+ 指标",
  "Chọn chỉ số": "选择指标",
  "Bật tối đa 5 chỉ số. Lưu trên điện thoại này.": "最多开启 5 个指标，保存在本手机上。",
  "Chưa chọn chỉ số nào": "未选择指标",
  "bấm ⚙": "点击 ⚙",
  "Tối đa 5 chỉ số mỗi biểu đồ": "每个图表最多 5 个指标",
  "Xuất ảnh": "导出图片", "Đã tải ảnh báo cáo": "已下载报告图片", "Chưa có số liệu để xuất.": "暂无可导出的数据。",
  "Không tải được thư viện xuất ảnh.": "无法加载图片导出库。",
  "Một số nguồn dữ liệu đọc lỗi": "部分数据源读取失败",
  // CSV
  "Nhóm": "分组", "Kỳ này": "本周期", "Kỳ so sánh": "对比周期", "% thay đổi": "变化 %",
  "Cả kỳ trước": "上一完整周期", "Tỷ lệ %": "比率 %", "Mới": "新", "điểm": "个百分点", "MM kỳ này": "本周期 MM",
  "Approved MM kỳ này": "本周期已批准 MM", "MM kỳ trước": "上一周期 MM",
  // Nhóm & thẻ KPI (metrics.py)
  "Bài đăng group & Link": "群组帖子与链接", "Data 4 kho → Match Making": "4 个管道数据 → Match Making",
  "Nguồn data: Tag & Source": "数据来源：标签与来源", "Chưa cấu hình kho": "尚未配置管道",
  "số deal tiến vào stage trong kỳ (không tính hồi sinh, kéo lùi, dời hàng loạt)": "本周期进入各阶段的商机数（不含复活、回退和批量移动）",
  "Deal mới tạo trong kỳ (mọi kho, gồm cả deal đã Lost) đến từ đâu": "本周期新建商机的来源（所有管道，包括已 Lost 的商机）",
  "Deal mới tạo + deal từ 4 kho chuyển sang (không tính hồi sinh)": "新建商机 + 从 4 个管道转入的商机（不含复活）",
  "MM được duyệt (Won) trong kỳ": "本周期已批准的 MM（Won）",
  "Content nộp": "已提交内容", "Đã duyệt, chưa đăng": "已批准，未发布", "Đã dùng để đăng": "已用于发布",
  "Chưa duyệt": "未审核", "Bị từ chối": "已拒绝", "Content gửi cho project XINYANG trong kỳ": "本周期提交给 XINYANG 项目的内容",
  "Đã duyệt, chờ dùng để đăng": "已批准，等待发布", "Đã dùng để đăng group (Archived)": "已用于群组发布（Archived）",
  "Bài đăng group Facebook": "Facebook 群组帖子", "Link đạt": "合格链接", "Link không đạt": "不合格链接",
  "Uncheck (chưa kiểm tra)": "Uncheck（未检查）", "Not Approved Links (bị chặn/xoá, lỗi)": "Not Approved Links（被屏蔽/删除、出错）",
  "Tổng data 4 kho → Match Making": "4 个管道数据 → Match Making 合计", "các kho": "各管道",
  "Chưa gán": "未分配", "Chưa gắn Tag": "无标签", "Chưa gắn Source": "无来源", "Không rõ": "未知", "Khác": "其他",
  "Chưa kết nối SGT Odoo": "未连接 SGT Odoo",
  "Không đọc được dữ liệu GB Submit (xem mục lỗi).": "无法读取 GB Submit 数据（请查看错误信息）。",
  // Biểu đồ (metrics.py)
  "Deal vào từng stage theo kỳ": "各周期进入各阶段的商机", "Số deal vào từng stage": "进入各阶段的商机数",
  "Phễu Match Making": "Match Making 漏斗", "Theo nhân sự": "按人员", "Mỗi thanh = 1 nhân sự": "每条 = 1 位人员",
  "màu = stage": "颜色 = 阶段", "Match Making & Approved MM theo kỳ": "各周期 Match Making 与已批准 MM",
  "MM và MM được duyệt": "MM 与已批准 MM", "Bảng xếp hạng MM theo nhân sự": "人员 MM 排行榜",
  "Xếp từ nhiều đến ít": "从多到少排序", "MM = deal vào 5.Match Making": "MM = 进入 5.Match Making 的商机",
  "Content theo kỳ": "各周期内容", "Content nộp & trạng thái": "已提交内容与状态",
  "Trạng thái content": "内容状态", "Content theo trạng thái": "按状态统计内容",
  "Content theo người nộp": "按提交人统计内容", "Mỗi thanh = 1 người nộp": "每条 = 1 位提交人",
  "Bài đăng group theo kỳ": "各周期群组帖子", "Đạt + Không đạt + Uncheck": "合格 + 不合格 + Uncheck",
  "Tỷ lệ link đạt theo kỳ": "各周期链接合格率", "Link đạt / tổng bài": "合格链接 / 帖子总数", "% link đạt": "链接合格率 %",
  "Kết quả link": "链接结果", "Đạt / không đạt / uncheck": "合格 / 不合格 / uncheck", "Bài đăng": "帖子",
  "Bài đăng theo người đăng": "按发布人统计帖子", "Mỗi thanh = 1 người đăng": "每条 = 1 位发布人",
  "Data 4 kho đổ vào Match Making theo kỳ": "各周期 4 个管道数据流入 Match Making", "Mỗi màu = 1 kho": "每种颜色 = 1 个管道",
  "Tỷ trọng theo kho": "按管道占比", "Tỷ trọng từng kho": "各管道占比",
  "Vào Match Making ở stage nào": "进入 Match Making 的阶段", "Stage nhận deal từ 4 kho": "接收 4 个管道商机的阶段",
  "Data đang nằm trong 4 kho (hiện tại)": "当前仍在 4 个管道中的数据", "Deal còn ở từng kho": "各管道剩余商机",
  "Deal đang ở kho": "管道中的商机", "Deal mới": "新商机", "1 deal nhiều tag tính ở mỗi tag": "一个商机有多个标签时，每个标签各计一次",
  // Bản đồ (map.html / map.js)
  "Bộ lọc bản đồ": "地图筛选", "Deal có x_address": "有 x_address 的商机", "Xóa bộ lọc": "清除筛选",
  "Bộ lọc khách hàng": "客户筛选", "Lớp bản đồ": "地图图层", "Khách hàng": "客户", "LỚP BẢN ĐỒ": "地图图层",
  "Chế độ hiển thị": "显示模式", "Điểm": "点位", "Mật độ": "密度",
  "Bật từng lớp hoặc cả hai. Số trong cụm là tổng khách hàng.": "可单独或同时开启图层。聚合点中的数字为客户总数。",
  "Bán kính vùng nhiệt": "热力半径", "Độ đậm": "强度", "Nền bản đồ": "底图", "Nền nhạt": "浅色", "Nền màu": "彩色",
  "Tìm sự kiện / ngành hàng": "搜索活动 / 行业", "Nhập sự kiện hoặc ngành hàng...": "输入活动或行业...",
  "BỘ LỌC CRM": "CRM 筛选", "Tất cả pipeline": "全部管道", "Tất cả stage": "全部阶段",
  "Nguồn dữ liệu (x_expo)": "数据来源（x_expo）", "Tất cả": "全部", "Sự kiện / ngành hàng (x_event)": "活动 / 行业（x_event）",
  "Tất cả x_event": "全部 x_event", "Vị trí sự kiện": "活动地点", "Tỉnh / Thành": "省 / 市", "Quận / Huyện": "区 / 县",
  "Tất cả nhân sự": "全部人员", "Tất cả tags": "全部标签", "Nguồn tọa độ": "坐标来源", "Tất cả nguồn": "全部来源",
  "Trạng thái tọa độ": "坐标状态", "Đã định vị": "已定位", "Chờ định vị": "等待定位",
  "Không tìm thấy": "未找到", "Thiếu hoặc sai tọa độ": "坐标缺失或错误",
  "Tổng hợp theo tỉnh / thành": "按省 / 市汇总", "Khu vực": "地区", "Khách": "客户", "Có GPS": "有 GPS",
  "Danh sách khách hàng": "客户列表", "Xem thêm": "查看更多", "Ẩn bộ lọc": "隐藏筛选", "Hiện bộ lọc": "显示筛选",
  "Toàn bộ điểm": "全部点位", "Đọc lại dữ liệu mới nhất từ Xinyang Odoo": "从 Xinyang Odoo 重新读取最新数据",
  "Đọc lại Odoo": "重新读取 Odoo", "Thưa → Dày": "稀疏 → 密集", "Bản đồ": "地图", "Chế độ": "模式",
  "Đang khởi tạo bản đồ": "正在初始化地图", "Dữ liệu từ Xinyang Odoo sẽ xuất hiện tại đây.": "Xinyang Odoo 的数据将显示在这里。",
  "Đang tải dữ liệu": "正在加载数据", "Đang tải dữ liệu…": "正在加载数据…", "Đóng": "关闭",
  "Không có x_event phù hợp": "没有匹配的 x_event", "Chưa có tỉnh/thành": "暂无省/市",
  "Địa chỉ CRM": "CRM 地址（x_address）", "Tỉnh/thành": "省/市", "Quận/huyện": "区/县",
  "Sự kiện": "活动", "Chưa có": "暂无", "Trạng thái (x_yp_geo_status)": "状态（x_geo_status）", "Có tọa độ": "有坐标",
  "Độ chính xác": "精度", "Nhà cung cấp (x_geo_provider)": "服务商（x_geo_provider）",
  "Địa chỉ GPS (x_geo_formatted_address)": "GPS 地址（x_geo_formatted_address）",
  "Mở Deal trong Xinyang Odoo": "在 Xinyang Odoo 中打开商机", "Xem chi tiết": "查看详情",
  "Đã tắt các lớp dữ liệu": "所有数据图层已关闭", "Bật Điểm hoặc Mật độ để xem khách hàng.": "开启点位或密度以查看客户。",
  "Chưa có deal có địa chỉ": "暂无带地址的商机", "Xinyang Odoo chưa có Deal nào có địa chỉ hoặc tọa độ.": "Xinyang Odoo 中还没有填写 x_address 的商机。",
  "Chưa có điểm GPS cho bộ lọc": "当前筛选条件下没有 GPS 点位",
  "Mạng hiện tại chặn các nguồn nền bản đồ. Điểm và bộ lọc vẫn sử dụng được.": "当前网络屏蔽了底图来源。点位和筛选仍可使用。",
  "Không tải được thư viện bản đồ": "无法加载地图库",
  "Tải lại trang hoặc kiểm tra các file static/vendor trong gói triển khai.": "请刷新页面或检查部署包中的 static/vendor 文件。",
  "Đọc trực tiếp Xinyang Odoo bằng tài khoản đang đăng nhập": "使用当前登录账号直接读取 Xinyang Odoo",
  "Chưa có Deal nào có địa chỉ": "暂无带 x_address 的商机", "Đang đồng bộ thủ công từ Xinyang Odoo": "正在从 Xinyang Odoo 手动同步",
  "Chưa cấu hình tài khoản Xinyang Odoo": "尚未配置 Xinyang Odoo 账号", "Lỗi đọc Xinyang Odoo": "读取 Xinyang Odoo 出错",
  "Kiểm tra quyền/fields": "请检查权限/字段", "cần cập nhật CRM-005 (Update 047)": "需要安装 CRM-005 插件",
  "Không đọc được dữ liệu": "无法读取数据",
  "Phiên đăng nhập dashboard đã hết hạn. Tải lại dashboard và đăng nhập lại.": "仪表板登录已过期。请刷新仪表板并重新登录。",
  "Đang đọc…": "正在读取…", "Đang đọc dữ liệu Xinyang Odoo…": "正在读取 Xinyang Odoo 数据…", "Chưa đăng nhập dashboard": "未登录仪表板",
  "Không đọc được dữ liệu bản đồ": "无法读取地图数据",
  // Bản đồ v4.16.0
  "Bật từng lớp hoặc cả hai. Cụm chia màu theo số deal của từng nhóm.": "可单独或同时开启图层。聚合点按各组商机数量分色。",
  "Tô màu theo": "着色依据",
  "Đổi màu": "修改颜色",
  "Khoảng cách gom cụm": "聚合距离",
  "Hiện cả deal gốc đã copy sang pipeline khác": "同时显示已复制到其他管道的原商机",
  "Tìm công ty / địa chỉ": "搜索公司 / 地址",
  "Tên công ty, địa chỉ, #ID...": "公司名称、地址、#ID...",
  "Số deal theo pipeline / stage": "按管道 / 阶段统计商机",
  "Cụm nhiều màu: chia theo số deal": "多色聚合：按商机数量分色",
  "MÀU TRÊN BẢN ĐỒ": "地图颜色",
  "Màu theo stage": "按阶段着色",
  "Màu theo Salesperson": "按销售员着色",
  "Màu theo pipeline": "按管道着色",
  "Màu mặc định": "默认颜色",
  "Hủy": "取消",
  "Lưu màu": "保存颜色",
  "Bấm để lọc theo tỉnh/thành này": "点击按此省/市筛选",
  "Bấm để xem từng stage của pipeline này": "点击查看该管道的各阶段",
  "Bấm để lọc theo stage này": "点击按此阶段筛选",
  "Chưa giao": "未分配",
  "Không có pipeline": "无管道",
  "Phóng to / tách điểm": "放大 / 展开点位",
  "Copy từ deal": "复制自商机",
  "Màu lưu trên trình duyệt này.": "颜色保存在此浏览器中。",
  "Mặc định đi từ lạnh đến nóng theo thứ tự stage trong pipeline: xám (mới) → xanh → cam → đỏ; stage Won màu xanh lá. Lưu theo ID stage nên đổi tên stage không mất màu.": "默认按管道内阶段顺序由冷到热：灰色（新）→ 蓝 → 橙 → 红；成交（Won）阶段为绿色。按阶段 ID 保存，阶段改名不丢失颜色。",
  "Dùng khi muốn xem khu vực của từng người phụ trách.": "用于查看每位负责人的区域。",
  "Dùng khi muốn so sánh vùng khách giữa các kho / pipeline.": "用于比较各管道的客户区域。",
  // Xuất báo cáo Dashboard (PDF)
  "Xuất báo cáo": "导出报告", "Xuất file Dashboard Report (PDF 4 trang, tiếng Anh)": "导出 Dashboard Report 文件（4 页 PDF，英文）",
  "Xuất báo cáo Dashboard (PDF)": "导出仪表板报告（PDF）",
  // Trình sửa báo cáo
  "Lấy lại số liệu gốc": "恢复原始数据", "Xem PDF": "查看 PDF", "Tải PDF": "下载 PDF",
  "Đọc lại số liệu Odoo và bỏ mọi chỗ đã sửa của kỳ này": "重新读取 Odoo 数据并放弃本周期的所有修改",
  "Mở file PDF đúng như khi tải về": "按下载后的样子打开 PDF", "Đóng (bản sửa được lưu nháp)": "关闭（修改已保存为草稿）",
  "Bấm vào chữ bất kỳ trên báo cáo để sửa · Enter trong danh sách để thêm ý · Ctrl+Z hoàn tác · tự lưu nháp theo từng kỳ":
    "点击报告中的任意文字即可编辑 · 在列表中按 Enter 添加要点 · Ctrl+Z 撤销 · 按周期自动保存草稿",
  "Đang đọc số liệu Odoo và dựng báo cáo...": "正在读取 Odoo 数据并生成报告...",
  "Đang đọc số liệu Odoo…": "正在读取 Odoo 数据…", "Đang sửa…": "编辑中…", "Báo cáo chưa sẵn sàng.": "报告尚未就绪。",
  "Đang tạo PDF...": "正在生成 PDF...", "Đang tạo PDF từ bản đang sửa...": "正在根据编辑后的报告生成 PDF...",
  "Không lưu được nháp (bộ nhớ trình duyệt đầy) — nhớ tải PDF trước khi đóng.": "无法保存草稿（浏览器存储已满）— 请在关闭前下载 PDF。",
  "Bỏ mọi chỗ đã sửa của kỳ này và đọc lại số liệu gốc từ Odoo?": "放弃本周期的所有修改并从 Odoo 重新读取原始数据？",
  "Chọn đủ Từ ngày và Đến ngày.": "请同时选择开始日期和结束日期。", "Đến ngày phải sau Từ ngày.": "结束日期必须晚于开始日期。",
  "Báo cáo quá lớn (tối đa 3 MB).": "报告过大（最大 3 MB）。", "Nội dung báo cáo không hợp lệ.": "报告内容无效。",
  "Báo cáo Dashboard": "仪表板报告",
  "Bấm vào chữ bất kỳ để sửa · rê chuột lên thẻ KPI để xoá/đổi chỗ, nút + Thêm thẻ KPI để thêm · Ctrl+Z hoàn tác chữ · tự lưu nháp theo từng kỳ":
    "点击任意文字即可编辑 · 鼠标悬停在 KPI 卡片上可删除/移动，点击 + 添加 KPI 卡片 · Ctrl+Z 撤销文字 · 按周期自动保存草稿",
  "Bấm vào chữ để sửa · rê chuột lên thẻ KPI để xoá/đổi chỗ, + Thêm thẻ KPI để thêm · ✕ Xoá trang ở góc mỗi trang · Ctrl+Z hoàn tác chữ · tự lưu nháp":
    "点击文字即可编辑 · 鼠标悬停在 KPI 卡片上可删除/移动，+ 添加 KPI 卡片 · 每页角落的 ✕ 删除页面 · Ctrl+Z 撤销文字 · 自动保存草稿",
  "Bấm vào chữ để sửa · rê chuột lên thẻ KPI để xoá/đổi chỗ, + Thêm thẻ KPI để thêm · ⚙ Đổi biểu đồ khi rê chuột lên biểu đồ · ✕ Xoá trang ở góc mỗi trang · tự lưu nháp":
    "点击文字即可编辑 · 鼠标悬停在 KPI 卡片上可删除/移动，+ 添加 KPI 卡片 · 鼠标悬停在图表上点击 ⚙ 更换图表 · 每页角落的 ✕ 删除页面 · 自动保存草稿",
  "Đổi biểu đồ": "更换图表",
  "Chỉ số": "指标", "tối đa": "最多", "Xoá biểu đồ": "删除图表", "Đã xoá biểu đồ": "已删除图表", "Khôi phục": "恢复",
  "Trang": "页面", "Đã xoá trang": "已删除页面", "khỏi báo cáo": "（从报告中）", "Khôi phục trang": "恢复页面", "Xoá trang": "删除页面",
  "Xoá trang này khỏi báo cáo (khôi phục lại được)": "从报告中删除此页（可恢复）",
  "Chuyển sang trái": "左移", "Chuyển sang phải": "右移", "Xoá thẻ": "删除卡片", "Thêm thẻ KPI": "添加 KPI 卡片",
  "Thẻ trống": "空白卡片", "Chỉ số khác": "其他指标", "tự nhập số và tên": "自行输入数值和名称", "Thẻ đã xoá": "已删除的卡片", "Sao chép từ": "复制自",
  "File 4 trang tiếng Anh giống mẫu Dashboard Report của Xinyang Weekly Report: Match Making · Content · Group Posts & Links · Data 4 Pools.":
    "4 页英文文件，版式与 Xinyang Weekly Report 的 Dashboard Report 相同：Match Making · Content · Group Posts & Links · Data 4 Pools。",
  "Kỳ báo cáo": "报告周期", "Từ ngày": "开始日期", "Đến ngày": "结束日期", "Tuần này": "本周", "Tuần trước": "上周",
  "Nhận xét thêm (tuỳ chọn · mỗi dòng 1 ý · ghi tiếng Anh nếu gửi khách)": "补充评论（可选 · 每行一条 · 发给客户请用英文）",
  "Additional activities (trang 1 · hoạt động ngoài hệ thống)": "Additional activities（第 1 页 · 系统外的活动）",
  "Số liệu đọc trực tiếp từ Xinyang Odoo + SGT Odoo bằng tài khoản đang đăng nhập; mỗi thẻ so với kỳ trước (cùng độ dài) và cùng ngày tháng trước. Nhận xét tự lưu trên trình duyệt theo từng kỳ.":
    "数据使用当前登录账号直接从 Xinyang Odoo + SGT Odoo 读取；每张卡片与上一周期（相同长度）及上月同期对比。评论按周期自动保存在浏览器中。",
  "Xem trước": "预览", "Báo cáo": "报告",
  "tuần đang chạy, số liệu tính đến hôm nay": "本周进行中，数据截至今天",
  "Hôm nay": "今天", "Hôm qua": "昨天", "hôm nay, số liệu tính đến lúc bấm xuất · so với hôm qua": "今天，数据截至点击导出时 · 与昨天对比",
  "so với hôm trước": "与前一天对比",
  "Đang tạo báo cáo từ Odoo...": "正在根据 Odoo 生成报告...", "Đang đọc số liệu Odoo và tạo PDF...": "正在读取 Odoo 数据并生成 PDF...",
  "Kỳ báo cáo tối đa 3 tháng.": "报告周期最长 3 个月。", "Ngày bắt đầu nằm trong tương lai.": "开始日期在未来。", "Bạn cần bật JavaScript để sử dụng bản đồ.": "需要启用 JavaScript 才能使用地图。",
};

// Mẫu câu có biến. tr = bộ dịch tiếng Trung (gọi đệ quy cho phần con); num = đổi 1.234 -> 1,234
const PATTERNS = (tr, num) => [
  // Nhãn kỳ
  [/^Tuần (\d{1,2})\/(\d{4})$/, (_, w, y) => `${y}年第${w}周`],
  [/^Tháng (\d{1,2})\/(\d{4})$/, (_, m, y) => `${y}年${+m}月`],
  [/^Năm (\d{4})$/, (_, y) => `${y}年`],
  [/^T(\d{1,2})\/(\d{4})$/, (_, m, y) => `${y}年${+m}月`],
  [/^T(\d{1,2})$/, (_, w) => `第${w}周`],
  [/^(\d+) (tuần|tháng|năm)$/, (_, n, g) => `${n}${{"tuần": "周", "tháng": "个月", "năm": "年"}[g]}`],
  // So sánh / bảng
  [/^(.+?) vs (.+)$/, (_, a, b) => `${tr(a)} vs ${tr(b)}`],
  [/^MM (.+)$/, (_, p) => `MM ${tr(p)}`],
  [/^Approved (.+)$/, (_, p) => `已批准 ${tr(p)}`],
  [/^(\d+) thẻ KPI đang ẩn$/, (_, n) => `已隐藏 ${n} 张 KPI 卡片`],
  [/^(\d+) biểu đồ đang ẩn$/, (_, n) => `已隐藏 ${n} 个图表`],
  [/^(\d+)\. (.+)$/, (_, n, rest) => `${n}. ${tr(rest)}`],
  [/^Cập nhật (.+?)( \(cache\))?$/, (_, t, c) => `更新于 ${t}${c ? "（缓存）" : ""}`],
  [/^Xuất lúc (.+)$/, (_, t) => `导出于 ${t}`],
  [/^tổng (.+)$/, (_, v) => `合计 ${num(v)}`],
  [/^Một số nguồn dữ liệu đọc lỗi: (.+)$/s, (_, e) => `部分数据源读取失败：${tr(e)}`],
  // metrics.py
  [/^Kho ([A-Z0-9 _&-]+)$/, (_, k) => `${k} 管道`],
  [/^Deal tiến lên (.+) trong kỳ$/, (_, s) => `本周期推进到 ${s} 的商机`],
  [/^(Chủ nhật|Thứ (\d)), (.+)$/, (_, w, n, d) => `${n ? "星期" + "一二三四五六"[+n - 2] : "星期日"}, ${d}`],
  [/^(\d+) ngày trước$/, (_, n) => `${n} 天前`],
  [/^([\d.,]+)% đạt$/, (_, v) => `${v}% 通过`],
  [/^Deal được tạo mới ở (.+) \(tính cả deal đã chuyển đi \/ Lost\)$/, (_, k) => `在 ${tr(k)} 新建的商机（含已转出 / Lost 的商机）`],
  [/^Deal từ (.+) chuyển vào Match Making \(mọi stage\)$/, (_, k) => `从 ${tr(k)} 转入 Match Making 的商机（任意阶段）`],
  [/^Deal mới theo (.+?) qua các kỳ$/, (_, f) => `各周期按 ${f} 统计的新商机`],
  [/^Deal mới theo ([^·]+)$/, (_, f) => `按 ${f} 统计的新商机`],
  [/^(.+): ([\d.,]+) deal mới$/, (_, p, n) => `${tr(p)}：${num(n)} 个新商机`],
  [/^Không tìm thấy project '(.+)' trong GB Submit \(SGT Odoo\)\.$/, (_, p) => `在 GB Submit（SGT Odoo）中未找到项目“${p}”。`],
  [/^Chưa đọc được GB Submit trên SGT Odoo: (.+)$/s, (_, e) => `无法读取 SGT Odoo 上的 GB Submit：${tr(e)}`],
  // odoo.py
  [/^Sai tài khoản\/mật khẩu (.+) \(DB: (.+)\)\.$/, (_, l, d) => `${l} 的账号/密码错误（DB：${d}）。`],
  [/^(.+) phản hồi quá chậm \(timeout\)\.$/, (_, l) => `${l} 响应过慢（timeout）。`],
  [/^Lỗi HTTP khi gọi (.+?): (.+)$/s, (_, l, e) => `调用 ${l} 时出现 HTTP 错误：${e}`],
  [/^Không kết nối được (.+) tại (.+) sau (\d+) lần thử (.+)$/s, (_, l, u, n, e) => `重试 ${n} 次后仍无法连接 ${l}（${u}）${e}`],
  [/^(.+) trả HTTP (\d+)\.$/, (_, l, c) => `${l} 返回 HTTP ${c}。`],
  [/^(.+) không trả JSON\.$/, (_, l) => `${l} 未返回 JSON。`],
  [/^(.+) từ chối quyền đọc: (.+)$/s, (_, l, m) => `${l} 拒绝读取权限：${m}`],
  [/^Xinyang Odoo chưa có field (.+) — cần cập nhật CRM-005 (Update 047)\.$/, (_, f) => `Xinyang Odoo 缺少字段 ${f} — 需要安装 CRM-005 插件。`],
  [/^Ngày không hợp lệ \(YYYY-MM-DD\)\.$/, () => "日期无效（YYYY-MM-DD）。"],
  // map.js
  [/^Tất cả x_event \(([\d.,]+)\)$/, (_, n) => `全部 x_event（${num(n)}）`],
  [/^([\d.,]+) bản ghi$/, (_, n) => `${num(n)} 条记录`],
  [/^([\d.,]+) có tọa độ \/ ([\d.,]+) khách hàng$/, (_, a, b) => `${num(a)} 个有坐标 / ${num(b)} 个客户`],
  [/^([\d.,]+) khách hàng phù hợp nhưng chưa có tọa độ\. Vào Odoo › Settings › Xinyang Map để chạy định vị\.$/,
    (_, n) => `${num(n)} 个符合条件的客户尚无坐标。请前往 Odoo › Settings › Xinyang Map 运行定位。`],
  [/^cache (\d+) phút$/, (_, n) => `缓存 ${n} 分钟`],
  [/^([\d.,]+) deal tại khu vực này$/, (_, n) => `该区域共 ${num(n)} 个商机`],
  [/^Xem thêm \(([\d.,]+)\)$/, (_, n) => `查看更多（${num(n)}）`],
  [/^([\d.,]+) deal gốc đã copy đang ẩn$/, (_, n) => `已隐藏 ${num(n)} 个已复制的原商机`],
  // Xuất báo cáo
  [/^Trang (\d+)$/, (_, n) => `第 ${n} 页`],
  [/^VD: (.+)$/s, (_, x) => `例：${x}`],
  [/^(\d+) ngày$/, (_, n) => `${n} 天`],
  [/^Đã tạo (.+) \(([\d.,]+) giây\)\.$/, (_, f, t) => `已生成 ${f}（${t} 秒）。`],
  [/^Đã tạo file nhưng một số số liệu đọc lỗi: (.+)$/s, (_, e) => `文件已生成，但部分数据读取失败：${e}`],
  [/^Chưa cài WeasyPrint trên server \((.+)\)\. Build lại bằng Dockerfile của bản (.+)\.$/s, (_, e, v) => `服务器未安装 WeasyPrint（${e}）。请使用 ${v} 版本的 Dockerfile 重新构建。`],
  [/^Đọc lúc (.+)$/, (_, t) => `读取于 ${t}`],
  [/^Đã lưu nháp lúc (.+)$/, (_, t) => `草稿已保存于 ${t}`],
  [/^Đã xoá trang (.+) — bấm "Khôi phục trang" nếu cần lại$/, (_, t) => `已删除页面 ${t} — 如需恢复请点击“恢复页面”`],
  [/^Đã khôi phục trang (.+)$/, (_, t) => `已恢复页面 ${t}`],
  [/^Tối đa (\d+) chỉ số trên 1 biểu đồ$/, (_, n) => `每个图表最多 ${n} 个指标`],
  [/^Trang (\d+) dài quá 1 tờ A4 — phần dưới vạch này sẽ sang trang mới trong PDF$/, (_, n) => `第 ${n} 页超过一张 A4 — 此线以下的内容在 PDF 中会移到新的一页`],
  [/^Số liệu Odoo đọc trong ([\d.,]+) giây · bấm vào chữ để sửa$/, (_, t) => `Odoo 数据读取用时 ${t} 秒 · 点击文字即可编辑`],
  [/^Một số số liệu đọc lỗi: (.+)$/s, (_, e) => `部分数据读取失败：${e}`],
  [/^Đang mở bản đã sửa \(lưu lúc (.+)\) · bấm "Lấy lại số liệu gốc" để đọc lại Odoo$/, (_, t) => `正在显示已编辑版本（保存于 ${t}）· 点击“恢复原始数据”重新读取 Odoo`],
  [/^Báo cáo: (.+)$/s, (_, x) => `报告：${x}`],
  [/^Ngày (\d\d\/\d\d\/\d{4})$/, (_, d) => `日期 ${d}`],
  [/^Lỗi: (.+)$/s, (_, e) => `错误：${tr(e)}`],
  // Câu tăng/giảm (tooltip)
  [/^(Tăng|Giảm) ([\d.,]+) điểm %$/, (_, w, n) => `${w === "Tăng" ? "增加" : "减少"} ${n} 个百分点`],
  [/^(Tăng|Giảm) ([\d.,]+) \(kỳ trước = 0\)$/, (_, w, n) => `${w === "Tăng" ? "增加" : "减少"} ${num(n)}（上一周期 = 0）`],
  [/^(Tăng|Giảm) ([\d.,]+) \(([+−-])([\d.,]+)%\)$/, (_, w, n, sg, p) => `${w === "Tăng" ? "增加" : "减少"} ${num(n)}（${sg}${p.replace(",", ".")}%）`],
  [/^Không đổi( \(0%\))?$/, (_, z) => `无变化${z ? "（0%）" : ""}`],
  // delta: "+12 Mới", "+12 (Mới)", "▲ 3,5 điểm"
  [/^(.*?)\(Mới\)$/, (_, a) => `${a}(新)`],
  [/^(.*?\S )?Mới$/, (_, a) => `${a || ""}新`],
  [/^(.*\d) điểm$/, (_, a) => `${a} 个百分点`],
  [/^(.*) \| (.+)$/, (_, a, b) => `${tr(a)} | ${tr(b)}`],
];

/* Khối HTML dài: Chú giải KPI */
const BLOCKS = {
  legend: `
  <h2>KPI 说明</h2>
  <p><b>对比方式：</b>选择 周 / 月 / 年。KPI 卡片显示当前周期的数值，以及与上一周期相比的增减 %。如果当前周期尚未结束，上一周期会截取相同天数（例如本周一→周三 对比 上周一→周三），以保证对比公平。</p>
  <h3>Match Making（Xinyang Odoo · History stage change）</h3>
  <p><b>1–6. Opportunity → Approved Match Making：</b>本周期<u>进入</u>该阶段的商机数，取自 History stage change 表。只统计真实的向前推进：新建商机、从 4 个管道转入的商机、从较低阶段向上推进的商机。<b>不统计：</b>复活的商机（退回 Opportunity）、被拉回较早阶段的商机，以及删除/修改阶段时批量移动的商机。过去周期的数据保持不变；同一商机在同一天多次进入同一阶段只计一次。</p>
  <p><b>1. Opportunity</b> = 本周期新建的商机 + 从 4 个管道转入 Match Making 的商机。<b>6. Approved Match Making</b> = Match Making 管道的 Won 阶段（已批准的 MM）。</p>
  <p>数字旁的小比率（卡片 2–6）= 该阶段数量 / 同周期 Opportunity 数量。</p>
  <p><b>人员 MM 排行榜：</b>每位人员在本周期将商机推进到 5.Match Making 阶段的数量（仅统计向前推进，与卡片 5 相同），从多到少排序；同时显示本周期已批准 MM、与上一周期的对比，以及最近几周/月/年的 MM 数。人员 = 阶段变更时商机的负责人（Salesperson）。</p>
  <h3>内容（SGT Odoo · GB Submit · 项目 XINYANG）</h3>
  <p><b>7. 已提交内容：</b>提交给 XINYANG 项目的所有内容，按内容创建日期统计。<b>8. 已批准，未发布：</b>状态为 Approved 的内容。<b>9. 已用于发布：</b>状态为 Archived（已使用）的内容。卡片 8 和 9 基于同一周期内提交的内容统计。</p>
  <h3>群组帖子与链接（SGT Odoo · Publishing History）</h3>
  <p><b>10. Facebook 群组帖子</b> = Total Published = 合格链接 + 不合格链接 + Uncheck。<b>11. 合格链接</b> = Approved Links（发布成功，检查通过）。<b>12. 不合格链接</b> = Not Approved Links（被屏蔽/删除、无帖子 ID、超时）。<b>Uncheck</b> = 新发布、尚未检查的链接。公式与 SGT 上的 GB Submit Summary 向导一致。</p>
  <h3>4 个管道数据 → Match Making（Xinyang Odoo）</h3>
  <p><b>13.</b> 本周期从 4 个管道（Inbound Pool、Outbound Data、Inbound GB、Outbound Hunter）转入 MATCH MAKING 管道的商机数，进入任意阶段（Opportunity 或其他）均计入。两种转移方式都统计：<b>移动</b>（商机离开原管道）和<b>复制</b>（原商机保留，Odoo 在 Match Making 中新建商机）。图表按管道拆分；“仍在 4 个管道中” = 仍停留在 4 个管道中且尚未到达 Approved 阶段的商机。</p>
  <p><b>14. 4 个管道新建数据：</b>本周期在 4 个管道中<u>新建</u>的商机数，按管道拆分（读取阶段变更历史中阶段属于该管道的“新建”记录）。之后已转入 Match Making 或 Lost 的商机仍按新建日期计入。卡片另显示<b>今天</b>（查看当前周期时）和<b>日均</b>；“每日新建数据”图表显示截至所查看周期末的最近各天（按周查看：14 天，可与上周对比；按月：整月；最多 31 天）；日均只计算所查看周期内的天数。与 Dashboard Report 中 “New data” 公式相同。</p>
  <h3>客户地图（Xinyang Odoo · 插件 CRM-005）</h3>
  <p>每个点代表一个带有 <b>x_address</b> 以及坐标 <b>x_latitude / x_longitude</b> 的商机。坐标由 CRM-005 插件使用 Gemini 定位（通常精确到坊/区），也可在商机上手动输入。<b>点位</b>会聚合显示，聚合点中的数字 = 客户数；<b>密度</b> = 热力图。点位和聚合按阶段着色（灰色 = 新 → 红色 = Match Making 中，绿色 = 已批准），可切换为按销售员 / 管道着色；聚合按商机数量分色。已复制到其他管道的原商机会被隐藏，确保 1 个客户 = 1 个点。可按管道、阶段、x_expo、x_event、省/区、销售员、标签筛选。数据使用当前登录账号读取并缓存 5 分钟；点击“重新读取 Odoo”可立即获取最新数据。</p>
  <h3>数据来源：标签与来源（Xinyang Odoo）</h3>
  <p>本周期在所有管道中<u>新建</u>的商机数（包括 Lost/已归档的商机，以免过去的数据发生变化；管道间转移时生成的副本<b>不</b>计入，因为不是新数据），按商机的 <b>Tags</b> 和 <b>Source</b> 字段拆分。一个商机有多个标签时，每个标签各计一次。跨周期图表显示前 7 个标签/来源，其余归入“其他”；未填写的归入“无标签”/“无来源”。</p>
  <h3>图表中本周期与上一周期的对比</h3>
  <p>每个图表都显示与上一周期相比的增减和 %（例如 “+12 (▲ 31.9%)”）（本周对比上周，本月对比上月…）。跨周期图表：每个数据系列的数值显示在标题正下方。当前周期图表：▲▼ 数值显示在每个柱/图例旁。表格视图增加变化 % 列。将鼠标悬停在任意一列上可查看与前一周期相比的 %。进行中的周期与上一周期相同天数对比；百分比（合格链接）按百分点对比。</p>
  <h3>显示 / 隐藏 KPI 卡片</h3>
  <p>将鼠标悬停在卡片上，点击角落的 ✕ 即可隐藏；或打开 <b>⚙ 自定义</b> → KPI 卡片逐个开关。保存在浏览器中。</p>
  <h3>排序</h3>
  <p>使用每个分组角落的 ▲▼ 按钮将整个分组上移/下移；每个图表上的 ▲▼ 按钮可调整其在分组内的位置。或打开 <b>⚙ 自定义</b> 在一处统一排列。“恢复默认”可恢复原始顺序。</p>
  <h3>图表</h3>
  <p>每个图表都可更换类型（柱状图、堆叠柱状图、折线图、面积图、条形图、堆叠条形图、饼图、环形图、表格）、更改宽度、显示/隐藏；点击图例项可显示/隐藏该数据系列。自定义设置保存在浏览器中。点击 KPI 卡片可跳转到对应图表。</p>
  <p><b>权限：</b>所有查询均使用当前登录的 Odoo 账号，因此 Odoo 的访问权限和记录规则依然有效。</p>`,
};

window.XINYANG_I18N_ZH = {dict: DICT, patterns: PATTERNS, blocks: BLOCKS};
})();
