/* Xinyang Report Dashboard — dịch giao diện Tiếng Việt → English / 中文 (v4.11.0)
 * Tiếng Trung: từ điển ở i18n_zh.js (nạp trước file này); chữ chưa có bản Trung dùng bản tiếng Anh.
 * Dịch bằng từ điển cài sẵn, không gọi dịch vụ ngoài, không gửi dữ liệu đi đâu.
 * - Chữ tĩnh + chữ do app.js / map.js render: MutationObserver dịch text node & thuộc tính (title, placeholder, aria-label).
 * - Số liệu từ /api/dashboard: XINYANG_I18N.payload() dịch tiêu đề, nhãn, tên series (để chữ vẽ trên canvas và CSV cũng là tiếng Anh).
 * - Dữ liệu Odoo (tên người, công ty, địa chỉ, tag tự đặt…) giữ nguyên.
 * - Lưu lựa chọn trên trình duyệt (localStorage "xinyang_map_lang"); mở link kèm ?lang=en / ?lang=zh để vào thẳng ngôn ngữ đó.
 * - Kiểm tra chữ chưa có trong từ điển: mở console, gõ XINYANG_I18N.missing() (tiếng Anh) hoặc XINYANG_I18N.missing("zh")
 */
(() => {
"use strict";
const KEY = "xinyang_map_lang";
const VN = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const GRAN_EN = {"tuần": ["week", "weeks"], "tháng": ["month", "months"], "năm": ["year", "years"]};
const enNum = s => String(s).replace(/\./g, ",");
const PERIOD_RE = /(^|[\s(·])T\d{1,2}(\/\d{4})?(?=$|[\s):·])/;
// Tiếng Việt không dấu ("Xem theo", "Data 4 kho", "Thanh ngang") cũng phải bắt được
const needs = s => VN.test(s) || PERIOD_RE.test(s) || /(^|[^\p{L}])kho($|[^\p{L}])/iu.test(s) || ASCII_KEYS.some(k => s.includes(k));

/* ------------------------------------------------------------ từ điển chính xác (đã trim) */
const DICT = {
  // Đăng nhập
  "Đăng nhập bằng tài khoản Odoo Xinyang. Số liệu GB Submit được đọc từ SGT Odoo bằng cùng tài khoản; quyền xem vẫn do Odoo kiểm soát.":
    "Sign in with your Xinyang Odoo account. GB Submit figures are read from SGT Odoo with the same account; access rights are still controlled by Odoo.",
  "Tài khoản Odoo": "Odoo account", "Mật khẩu": "Password", "Đăng nhập": "Sign in", "Đang đăng nhập...": "Signing in...",
  "dữ liệu giả": "mock data", "Vui lòng đăng nhập bằng tài khoản Odoo Xinyang.": "Please sign in with your Xinyang Odoo account.",
  "Vui lòng nhập đầy đủ tài khoản và mật khẩu Odoo.": "Please enter both your Odoo username and password.",
  // Sidebar & topbar
  "ĐI NHANH": "QUICK JUMP", "BẢN ĐỒ": "MAP", "Tổng quan KPI": "KPI Overview", "Dữ liệu & làm mới": "Data & refresh",
  "Chú giải KPI": "KPI Glossary", "Bản đồ khách hàng": "Customer Map", "Chưa tải dữ liệu": "No data loaded yet",
  "Bài đăng group": "Group posts", "Data 4 kho": "4-pipeline data", "Tuỳ chỉnh": "Customize", "Làm mới": "Refresh",
  "Xuất CSV": "Export CSV", "Đăng xuất": "Log out",
  "Trạng thái kết nối Odoo và payload gần nhất": "Odoo connection status and latest payload",
  "Định nghĩa và cách tính từng chỉ số": "Definitions and calculation of each metric",
  "Heatmap & vị trí deal theo x_address": "Heatmap & deal locations by x_address",
  // Bộ lọc kỳ
  "Xem theo": "View by", "Tuần": "Week", "Tháng": "Month", "Năm": "Year", "Kỳ đang xem": "Viewing period",
  "Kỳ trước": "Previous period", "Kỳ sau": "Next period", "Chọn 1 ngày bất kỳ trong kỳ": "Pick any date within the period",
  "Kỳ hiện tại": "This period", "Số kỳ so sánh trên biểu đồ": "Periods compared on charts", "(cùng số ngày)": "(same number of days)",
  "Đang đọc dữ liệu Odoo...": "Loading Odoo data...", "kỳ trước": "previous period", "Trước": "Previous", "cả": "full period",
  // Trang dữ liệu
  "Lần tải gần nhất": "Last load", "Trạng thái dữ liệu": "Data status", "Payload lần tải gần nhất": "Payload from the last load",
  "Đọc lại từ Odoo": "Reload from Odoo", "Bản đồ khách hàng Xinyang": "Xinyang customer map", "Tắt": "Off",
  "đã kết nối": "connected", "chưa kết nối": "not connected", "tổng": "total",
  // Drawer tuỳ chỉnh
  "Tuỳ chỉnh dashboard": "Customize dashboard",
  "Chọn biểu đồ hiển thị, loại biểu đồ và độ rộng. Lưu trên trình duyệt này.": "Choose which charts to show, chart type and width. Saved in this browser.",
  "Khôi phục mặc định": "Restore defaults", "Xong": "Done", "Thẻ KPI": "KPI cards", "Hiện tất cả": "Show all", "Biểu đồ": "Charts",
  "Lên": "Up", "Xuống": "Down", "Nửa hàng": "Half width", "Cả hàng": "Full width", "Tải dữ liệu trước khi tuỳ chỉnh.": "Load data before customizing.",
  // Loại biểu đồ & công cụ
  "Bảng xếp hạng": "Leaderboard", "Cột": "Column", "Cột chồng": "Stacked column", "Đường": "Line", "Vùng": "Area",
  "Thanh ngang": "Horizontal bar", "Thanh ngang chồng": "Stacked horizontal bar", "Tròn": "Pie", "Bảng": "Table",
  "Ẩn thẻ này": "Hide this card", "hiện lại": "show again", "Đưa nhóm này lên trên": "Move this group up",
  "Đưa nhóm này xuống dưới": "Move this group down", "Đưa biểu đồ lên trước": "Move chart up", "Đưa biểu đồ xuống sau": "Move chart down",
  "Loại biểu đồ": "Chart type", "Đổi độ rộng": "Change width", "Ẩn biểu đồ": "Hide chart",
  "Chưa có MM nào trong các kỳ này": "No MM in these periods", "Chưa có dữ liệu trong kỳ này": "No data in this period",
  "Chưa có dữ liệu": "No data", "TỔNG": "TOTAL", "Tổng": "Total", "Nhân sự": "Staff", "Kỳ": "Period", "Mục": "Item",
  "Đang tồn ở 4 kho": "Currently in the 4 pipelines", "Chưa có kho nào": "No pipelines yet",
  "Data tạo mới trong 4 kho": "New data in the 4 pipelines", "Data tạo mới trong 4 kho theo kỳ": "New data in the 4 pipelines by period",
  "Data tạo mới mỗi ngày": "New data per day", "Mỗi cột = 1 ngày": "Each bar = 1 day", "mỗi màu = 1 kho": "each color = 1 pipeline",
  "Trung bình / ngày": "Average / day",
  // Báo cáo ngày mobile (v4.13.0)
  "Báo cáo ngày": "Daily report", "Data trong ngày": "Daily data", "Deal tạo mới ở 4 kho": "Deals created in the 4 pipelines",
  "Deal tiến vào stage trong ngày": "Deals advancing into a stage that day", "Bài post FB": "FB posts", "Bài đăng group Facebook (GB Submit)": "Facebook group posts (GB Submit)",
  "Tổng bài đăng": "Total posts", "Content nộp cho project XINYANG": "Content submitted to project XINYANG", "Chưa duyệt": "Not reviewed",
  "Mở dashboard đầy đủ": "Open full dashboard", "Ngày trước": "Previous day", "Ngày sau": "Next day", "Chọn ngày": "Pick a date",
  "Dùng tài khoản Odoo Xinyang.": "Use your Xinyang Odoo account.", "Đăng nhập thất bại.": "Sign-in failed.", "Không kết nối được máy chủ.": "Cannot reach the server.",
  "Không đọc được dữ liệu kho": "Could not read pipeline data", "Không đọc được Match Making": "Could not read Match Making",
  "Không đọc được bài đăng": "Could not read posts", "Không đọc được content": "Could not read content", "Chưa kết nối SGT Odoo": "SGT Odoo not connected",
  "Báo cáo ngày (mobile)": "Daily report (mobile)",
  "Nhận xét": "Comments",
  "Nhập nhận xét trong ngày (tự lưu, có trong ảnh xuất)": "Type today's comments (auto-saved, included in the exported image)",
  "Đang lưu…": "Saving…",
  "Đã lưu": "Saved",
  "Không lưu được trên trình duyệt này": "Could not save in this browser",
  "Chỉ số trong ngày": "Today's figures",
  "Data mới": "New data",
  "vào stage": "entering stage",
  "Tổng data mới (4 kho)": "Total new data (4 pipelines)",
  "Tổng data mới": "Total new data",
  "4 kho → MM": "4 pipelines → MM",
  "Tổng bài": "Total posts",
  "Không đạt": "Failed",
  "Content chưa duyệt": "Content not reviewed",
  "Content đã duyệt, chưa đăng": "Content approved, not posted",
  "Content đã dùng để đăng": "Content used for posting",
  "Đã duyệt": "Approved",
  "Đã dùng": "Used",
  "Data & Match Making": "Data & Match Making",
  "Bài đăng & Content": "Posts & Content",
  "+ Chỉ số": "+ Metric",
  "Chọn chỉ số": "Choose metrics",
  "Bật tối đa 5 chỉ số. Lưu trên điện thoại này.": "Turn on up to 5 metrics. Saved on this phone.",
  "Chưa chọn chỉ số nào": "No metric selected",
  "bấm ⚙": "tap ⚙",
  "Tối đa 5 chỉ số mỗi biểu đồ": "Up to 5 metrics per chart",
  "Xuất ảnh": "Export image", "Đã tải ảnh báo cáo": "Report image downloaded", "Chưa có số liệu để xuất.": "No figures to export yet.",
  "Không tải được thư viện xuất ảnh.": "Could not load the image export library.", "XINYANG": "XINYANG",
  "Một số nguồn dữ liệu đọc lỗi": "Some data sources failed to load",
  // CSV
  "Nhóm": "Group", "Kỳ này": "This period", "Kỳ so sánh": "Comparison period", "% thay đổi": "% change",
  "Cả kỳ trước": "Full previous period", "Tỷ lệ %": "Rate %", "Mới": "New", "điểm": "pts", "MM kỳ này": "MM this period",
  "Approved MM kỳ này": "Approved MM this period", "MM kỳ trước": "MM previous period",
  // Nhóm & thẻ KPI (metrics.py)
  "Bài đăng group & Link": "Group posts & Links", "Data 4 kho → Match Making": "4-pipeline data → Match Making",
  "Nguồn data: Tag & Source": "Data sources: Tag & Source", "Chưa cấu hình kho": "No pipelines configured",
  "số deal tiến vào stage trong kỳ (không tính hồi sinh, kéo lùi, dời hàng loạt)": "deals advancing into each stage in the period (excluding revivals, rollbacks and bulk moves)",
  "Deal mới tạo trong kỳ (mọi kho, gồm cả deal đã Lost) đến từ đâu": "Where deals created in the period came from (all pipelines, including Lost deals)",
  "Deal mới tạo + deal từ 4 kho chuyển sang (không tính hồi sinh)": "New deals + deals moved in from the 4 pipelines (excluding revivals)",
  "MM được duyệt (Won) trong kỳ": "MM approved (Won) in the period",
  "Content nộp": "Content submitted", "Đã duyệt, chưa đăng": "Approved, not yet posted", "Đã dùng để đăng": "Used for posting",
  "Chưa duyệt": "Not yet approved", "Bị từ chối": "Rejected", "Content gửi cho project XINYANG trong kỳ": "Content sent to project XINYANG in the period",
  "Đã duyệt, chờ dùng để đăng": "Approved, waiting to be posted", "Đã dùng để đăng group (Archived)": "Used for group posting (Archived)",
  "Bài đăng group Facebook": "Facebook group posts", "Link đạt": "Passed links", "Link không đạt": "Failed links",
  "Uncheck (chưa kiểm tra)": "Uncheck (not checked yet)", "Not Approved Links (bị chặn/xoá, lỗi)": "Not Approved Links (blocked/deleted, errors)",
  "Tổng data 4 kho → Match Making": "Total 4-pipeline data → Match Making", "các kho": "the pipelines",
  "Chưa gán": "Unassigned", "Chưa gắn Tag": "No tag", "Chưa gắn Source": "No source", "Không rõ": "Unknown", "Khác": "Other",
  "Chưa kết nối SGT Odoo": "SGT Odoo not connected",
  "Không đọc được dữ liệu GB Submit (xem mục lỗi).": "Could not read GB Submit data (see errors).",
  // Biểu đồ (metrics.py)
  "Deal vào từng stage theo kỳ": "Deals entering each stage by period", "Số deal vào từng stage": "Number of deals entering each stage",
  "Phễu Match Making": "Match Making funnel", "Theo nhân sự": "By staff", "Mỗi thanh = 1 nhân sự": "Each bar = 1 staff member",
  "màu = stage": "color = stage", "Match Making & Approved MM theo kỳ": "Match Making & Approved MM by period",
  "MM và MM được duyệt": "MM and approved MM", "Bảng xếp hạng MM theo nhân sự": "MM leaderboard by staff",
  "Xếp từ nhiều đến ít": "Sorted from most to least", "MM = deal vào 5.Match Making": "MM = deals entering 5.Match Making",
  "Content theo kỳ": "Content by period", "Content nộp & trạng thái": "Content submitted & status",
  "Trạng thái content": "Content status", "Content theo trạng thái": "Content by status",
  "Content theo người nộp": "Content by submitter", "Mỗi thanh = 1 người nộp": "Each bar = 1 submitter",
  "Bài đăng group theo kỳ": "Group posts by period", "Đạt + Không đạt + Uncheck": "Passed + Failed + Uncheck",
  "Tỷ lệ link đạt theo kỳ": "Link pass rate by period", "Link đạt / tổng bài": "Passed links / total posts", "% link đạt": "% passed links",
  "Kết quả link": "Link results", "Đạt / không đạt / uncheck": "Passed / failed / uncheck", "Bài đăng": "Posts",
  "Bài đăng theo người đăng": "Posts by poster", "Mỗi thanh = 1 người đăng": "Each bar = 1 poster",
  "Data 4 kho đổ vào Match Making theo kỳ": "4-pipeline data into Match Making by period", "Mỗi màu = 1 kho": "Each color = 1 pipeline",
  "Tỷ trọng theo kho": "Share by pipeline", "Tỷ trọng từng kho": "Share of each pipeline",
  "Vào Match Making ở stage nào": "Match Making entry stage", "Stage nhận deal từ 4 kho": "Stages receiving deals from the 4 pipelines",
  "Data đang nằm trong 4 kho (hiện tại)": "Data currently in the 4 pipelines", "Deal còn ở từng kho": "Deals remaining in each pipeline",
  "Deal đang ở kho": "Deals in pipeline", "Deal mới": "New deals", "1 deal nhiều tag tính ở mỗi tag": "a deal with several tags counts under each tag",
  // Bản đồ (map.html / map.js)
  "Bộ lọc bản đồ": "Map filters", "Deal CRM có địa chỉ · Xinyang Odoo": "CRM deals with an address · Xinyang Odoo", "Địa chỉ CRM": "CRM address", "Latitude (x_yp_latitude)": "Latitude (x_yp_latitude)", "Longitude (x_yp_longitude)": "Longitude (x_yp_longitude)", "Trạng thái (x_yp_geo_status)": "Status (x_yp_geo_status)", "Deal có x_address": "Deals with x_address", "Xóa bộ lọc": "Clear filters",
  "Bộ lọc khách hàng": "Customer filters", "Lớp bản đồ": "Map layers", "Khách hàng": "Customers", "LỚP BẢN ĐỒ": "MAP LAYER",
  "Chế độ hiển thị": "Display mode", "Điểm": "Points", "Mật độ": "Density",
  "Bật từng lớp hoặc cả hai. Số trong cụm là tổng khách hàng.": "Turn on either layer or both. The number in a cluster is the customer count.",
  "Bán kính vùng nhiệt": "Heat radius", "Độ đậm": "Intensity", "Nền bản đồ": "Basemap", "Nền nhạt": "Light", "Nền màu": "Color",
  "Tìm sự kiện / ngành hàng": "Search event / industry", "Nhập sự kiện hoặc ngành hàng...": "Type an event or industry...",
  "BỘ LỌC CRM": "CRM FILTERS", "Tất cả pipeline": "All pipelines", "Tất cả stage": "All stages",
  "Nguồn dữ liệu (x_expo)": "Data source (x_expo)", "Tất cả": "All", "Sự kiện / ngành hàng (x_event)": "Event / industry (x_event)",
  "Tất cả x_event": "All x_event", "Vị trí sự kiện": "Event location", "Tỉnh / Thành": "Province / City", "Quận / Huyện": "District",
  "Tất cả nhân sự": "All staff", "Tất cả tags": "All tags", "Nguồn tọa độ": "Coordinate source", "Tất cả nguồn": "All sources",
  "Trạng thái tọa độ": "Coordinate status", "Đã định vị": "Geocoded", "Chờ định vị": "Waiting for geocoding",
  "Không tìm thấy": "Not found", "Thiếu hoặc sai tọa độ": "Missing or invalid coordinates",
  "Tổng hợp theo tỉnh / thành": "Summary by province / city", "Khu vực": "Area", "Khách": "Customers", "Có GPS": "With GPS",
  "Danh sách khách hàng": "Customer list", "Xem thêm": "Show more", "Ẩn bộ lọc": "Hide filters", "Hiện bộ lọc": "Show filters",
  "Toàn bộ điểm": "All points", "Đọc lại dữ liệu mới nhất từ Xinyang Odoo": "Reload the latest data from Xinyang Odoo",
  "Đọc lại Odoo": "Reload Odoo", "Thưa → Dày": "Sparse → Dense", "Bản đồ": "Map", "Chế độ": "Mode",
  "Đang khởi tạo bản đồ": "Initializing map", "Dữ liệu từ Xinyang Odoo sẽ xuất hiện tại đây.": "Data from Xinyang Odoo will appear here.",
  "Đang tải dữ liệu": "Loading data", "Đang tải dữ liệu…": "Loading data…", "Đóng": "Close",
  "Không có x_event phù hợp": "No matching x_event", "Chưa có tỉnh/thành": "No province/city",
  "Địa chỉ CRM": "CRM address (x_address)", "Tỉnh/thành": "Province/City", "Quận/huyện": "District",
  "Sự kiện": "Event", "Chưa có": "None", "Trạng thái (x_yp_geo_status)": "Status (x_geo_status)", "Có tọa độ": "Has coordinates",
  "Độ chính xác": "Accuracy", "Nhà cung cấp (x_geo_provider)": "Provider (x_geo_provider)",
  "Địa chỉ GPS (x_geo_formatted_address)": "GPS address (x_geo_formatted_address)",
  "Mở Deal trong Xinyang Odoo": "Open deal in Xinyang Odoo", "Xem chi tiết": "View details",
  "Đã tắt các lớp dữ liệu": "All data layers are off", "Bật Điểm hoặc Mật độ để xem khách hàng.": "Turn on Points or Density to see customers.",
  "Chưa có deal có địa chỉ": "No deals with an address yet", "Xinyang Odoo chưa có Deal nào có địa chỉ hoặc tọa độ.": "No deal in Xinyang Odoo has an address or coordinates yet.",
  "Chưa có điểm GPS cho bộ lọc": "No GPS points for this filter",
  "Mạng hiện tại chặn các nguồn nền bản đồ. Điểm và bộ lọc vẫn sử dụng được.": "The current network blocks the basemap sources. Points and filters still work.",
  "Không tải được thư viện bản đồ": "Could not load the map library",
  "Tải lại trang hoặc kiểm tra các file static/vendor trong gói triển khai.": "Reload the page or check the static/vendor files in the deployment package.",
  "Đọc trực tiếp Xinyang Odoo bằng tài khoản đang đăng nhập": "Read directly from Xinyang Odoo with the signed-in account",
  "Chưa có Deal nào có địa chỉ": "No deals with an address yet", "Đang đồng bộ thủ công từ Xinyang Odoo": "Syncing manually from Xinyang Odoo",
  "Chưa cấu hình tài khoản Xinyang Odoo": "Xinyang Odoo account not configured", "Lỗi đọc Xinyang Odoo": "Error reading Xinyang Odoo",
  "Kiểm tra quyền/fields": "Check permissions/fields", "cần cập nhật CRM-005 (Update 047)": "CRM-005 (Update 047) must be installed",
  "Không đọc được dữ liệu": "Could not read data",
  "Phiên đăng nhập dashboard đã hết hạn. Tải lại dashboard và đăng nhập lại.": "Your dashboard session has expired. Reload the dashboard and sign in again.",
  "Đang đọc…": "Loading…", "Đang đọc dữ liệu Xinyang Odoo…": "Loading Xinyang Odoo data…", "Chưa đăng nhập dashboard": "Not signed in to the dashboard",
  "Không đọc được dữ liệu bản đồ": "Could not read map data",
  // Bản đồ v4.16.0
  "Bật từng lớp hoặc cả hai. Cụm chia màu theo số deal của từng nhóm.": "Turn on either layer or both. Clusters are split into colours by deal count per group.",
  "Tô màu theo": "Colour by",
  "Đổi màu": "Change colours",
  "Khoảng cách gom cụm": "Cluster distance",
  "Hiện cả deal gốc đã copy sang pipeline khác": "Also show original deals already copied to another pipeline",
  "Tìm công ty / địa chỉ": "Search company / address",
  "Tên công ty, địa chỉ, #ID...": "Company name, address, #ID...",
  // Update 096: độ chính xác tọa độ (CRM-005 x_yp_geo_precision)
  "Độ chính xác tọa độ": "Coordinate accuracy", "Độ chính xác / nguồn tọa độ": "Accuracy / coordinate source",
  "Địa chỉ": "Address", "Phường/xã (ước lượng)": "Ward / area (estimated)", "Thành phố (ước lượng)": "City (estimated)", "Tỉnh/thành (ước lượng)": "Province / region (estimated)", "Nhập tay": "Manual",
  "≈ Phường/xã (ước lượng)": "≈ Ward / area (estimated)", "≈ Thành phố (ước lượng)": "≈ City (estimated)", "≈ Tỉnh/thành (ước lượng)": "≈ Province / region (estimated)", "≈ Contact": "≈ Contact",
  // Update 096: lọc nhanh
  "Hiển thị Deal": "Show deals", "Đã lên bản đồ": "On the map", "Chưa lên bản đồ": "Not on the map", "Deal đã lên bản đồ": "Deals on the map",
  // Update 095: 2 chế độ
  "Chế độ bản đồ": "Map mode", "Toàn bộ dữ liệu": "All data", "Potential Map": "Potential Map",
  "Mọi Deal CRM có địa chỉ, tô màu theo Stage.": "Every CRM deal with an address, coloured by Stage.",
  "Deal CRM có địa chỉ + Contact MM/Approved · Xinyang Odoo": "CRM deals with an address + MM/Approved Contacts · Xinyang Odoo",
  "Mọi Deal CRM đang active + Contact MM/Approved · Xinyang Odoo": "All active CRM deals + MM/Approved Contacts · Xinyang Odoo",
  "Mọi Deal CRM đang active, tô màu theo Stage. Deal chưa có tọa độ dùng tọa độ của Contact; Deal chưa có cả hai nằm ở danh sách Chờ định vị. Cộng thêm Contact MM/Approved từ bản đồ cũ.": "Every active CRM deal, coloured by Stage. A deal without coordinates uses its Contact's coordinates; a deal with neither stays in the Waiting-for-geocoding list. Plus the MM/Approved Contacts of the old map.",
  "Không đọc được tọa độ Contact của Deal": "Could not read the Contact coordinates of the deals",
  "Tọa độ lấy từ Contact (partner_latitude / partner_longitude)": "Coordinates taken from the Contact (partner_latitude / partner_longitude)",
  "Mọi Deal CRM có địa chỉ cùng các Contact ở Match Making / Approved Match Making (từ bản đồ cũ), tô màu theo Stage.": "Every CRM deal with an address plus the Contacts in Match Making / Approved Match Making (from the old map), coloured by Stage.",
  "Không đọc được Contact MM/Approved": "Could not read MM/Approved Contacts",
  "Contact có Deal ở Match Making & Approved Match Making · Xinyang Odoo": "Contacts with deals in Match Making & Approved Match Making · Xinyang Odoo",
  "Mỗi Công ty một điểm. Chỉ hiện Contact có Deal ở 5.Match Making hoặc 6.Approved Match Making (vàng = MM, xanh lá = Approved, xanh ngọc = cả hai).": "One point per company. Only Contacts with a deal in 5.Match Making or 6.Approved Match Making (yellow = MM, green = Approved, teal = both).",
  "Tìm Contact / công ty / địa chỉ": "Search Contact / company / address", "Tìm Contact / công ty / thành phố": "Search Contact / company / city",
  "Tên Contact, công ty, địa chỉ, #ID...": "Contact name, company, address, #ID...", "Tên công ty, thành phố...": "Company name, city...",
  "Danh sách Contact tiềm năng": "Potential Contact list",
  "Chưa có Contact tiềm năng": "No potential Contacts yet",
  "Chưa có Contact có tọa độ nào có Deal ở 5.Match Making hoặc 6.Approved Match Making.": "No Contact with coordinates has a deal in 5.Match Making or 6.Approved Match Making yet.",
  "Chưa có Contact nào có Deal ở Match Making / Approved Match Making": "No Contact has a deal in Match Making / Approved Match Making yet",
  "Mở Contact trong Xinyang Odoo": "Open Contact in Xinyang Odoo", "Contact ID": "Contact ID", "Nhóm": "Group",
  "Số Deal 5.Match Making": "Deals in 5.Match Making", "Số Deal 6.Approved Match Making": "Deals in 6.Approved Match Making",
  "Số Contact trong điểm": "Contacts in this point", "Thành phố / Quốc gia": "City / Country", "Đã lưu trữ": "Archived",
  "Latitude (partner_latitude)": "Latitude (partner_latitude)", "Longitude (partner_longitude)": "Longitude (partner_longitude)",
  "Cả 5.MM và 6.Approved": "Both 5.MM and 6.Approved", 
  "Số deal theo pipeline / stage": "Deals by pipeline / stage",
  "Cụm nhiều màu: chia theo số deal": "Multi-colour cluster: split by deal count",
  "MÀU TRÊN BẢN ĐỒ": "MAP COLOURS",
  "Màu theo stage": "Colours by stage",
  "Màu theo Salesperson": "Colours by salesperson",
  "Màu theo pipeline": "Colours by pipeline",
  "Màu mặc định": "Default colours",
  "Hủy": "Cancel",
  "Lưu màu": "Save colours",
  "Bấm để lọc theo tỉnh/thành này": "Click to filter by this province/city",
  "Bấm để xem từng stage của pipeline này": "Click to see each stage of this pipeline",
  "Bấm để lọc theo stage này": "Click to filter by this stage",
  "Chưa giao": "Unassigned",
  "Không có pipeline": "No pipeline",
  "Phóng to / tách điểm": "Zoom in / split points",
  "Copy từ deal": "Copied from deal",
  "Màu lưu trên trình duyệt này.": "Colours are saved in this browser.",
  "Mặc định đi từ lạnh đến nóng theo thứ tự stage trong pipeline: xám (mới) → xanh → cam → đỏ; stage Won màu xanh lá. Lưu theo ID stage nên đổi tên stage không mất màu.": "By default colours go from cold to hot following the stage order in each pipeline: grey (new) → blue → orange → red; Won stages are green. Saved by stage ID, so renaming a stage keeps its colour.",
  "Dùng khi muốn xem khu vực của từng người phụ trách.": "Use this to see each salesperson's area.",
  "Dùng khi muốn so sánh vùng khách giữa các kho / pipeline.": "Use this to compare customer areas between pipelines.",
  // Xuất báo cáo Dashboard (PDF) — v4.7.0
  "Xuất báo cáo": "Export report", "Xuất file Dashboard Report (PDF 4 trang, tiếng Anh)": "Export the Dashboard Report file (4-page PDF, English)",
  "Xuất báo cáo Dashboard (PDF)": "Export Dashboard Report (PDF)",
  // Trình sửa báo cáo (v4.8.0)
  "Lấy lại số liệu gốc": "Reload original figures", "Xem PDF": "View PDF", "Tải PDF": "Download PDF",
  "Đọc lại số liệu Odoo và bỏ mọi chỗ đã sửa của kỳ này": "Re-read Odoo figures and discard all edits for this period",
  "Mở file PDF đúng như khi tải về": "Open the PDF exactly as it will be downloaded", "Đóng (bản sửa được lưu nháp)": "Close (edits are saved as a draft)",
  "Bấm vào chữ bất kỳ trên báo cáo để sửa · Enter trong danh sách để thêm ý · Ctrl+Z hoàn tác · tự lưu nháp theo từng kỳ":
    "Click any text in the report to edit · Enter in a list adds a point · Ctrl+Z to undo · drafts auto-save per period",
  "Đang đọc số liệu Odoo và dựng báo cáo...": "Reading Odoo figures and building the report...",
  "Đang đọc số liệu Odoo…": "Reading Odoo figures…", "Đang sửa…": "Editing…", "Báo cáo chưa sẵn sàng.": "The report is not ready yet.",
  "Đang tạo PDF...": "Creating PDF...", "Đang tạo PDF từ bản đang sửa...": "Creating the PDF from the edited report...",
  "Không lưu được nháp (bộ nhớ trình duyệt đầy) — nhớ tải PDF trước khi đóng.": "Could not save the draft (browser storage is full) — download the PDF before closing.",
  "Bỏ mọi chỗ đã sửa của kỳ này và đọc lại số liệu gốc từ Odoo?": "Discard all edits for this period and re-read the original figures from Odoo?",
  "Chọn đủ Từ ngày và Đến ngày.": "Select both From and To dates.", "Đến ngày phải sau Từ ngày.": "The To date must be after the From date.",
  "Báo cáo quá lớn (tối đa 3 MB).": "The report is too large (max 3 MB).", "Nội dung báo cáo không hợp lệ.": "Invalid report content.",
  "Báo cáo Dashboard": "Dashboard report",
  "Bấm vào chữ bất kỳ để sửa · rê chuột lên thẻ KPI để xoá/đổi chỗ, nút + Thêm thẻ KPI để thêm · Ctrl+Z hoàn tác chữ · tự lưu nháp theo từng kỳ":
    "Click any text to edit · hover a KPI card to delete/move it, use + Add KPI card to add · Ctrl+Z undoes text · drafts auto-save per period",
  "Bấm vào chữ để sửa · rê chuột lên thẻ KPI để xoá/đổi chỗ, + Thêm thẻ KPI để thêm · ✕ Xoá trang ở góc mỗi trang · Ctrl+Z hoàn tác chữ · tự lưu nháp":
    "Click text to edit · hover a KPI card to delete/move it, + Add KPI card to add · ✕ Delete page in each page corner · Ctrl+Z undoes text · drafts auto-save",
  "Bấm vào chữ để sửa · rê chuột lên thẻ KPI để xoá/đổi chỗ, + Thêm thẻ KPI để thêm · ⚙ Đổi biểu đồ khi rê chuột lên biểu đồ · ✕ Xoá trang ở góc mỗi trang · tự lưu nháp":
    "Click text to edit · hover a KPI card to delete/move it, + Add KPI card to add · ⚙ Change chart when hovering a chart · ✕ Delete page in each page corner · drafts auto-save",
  "Đổi biểu đồ": "Change chart", "Loại biểu đồ": "Chart type", "Đường": "Line", "Cột": "Column", "Cột chồng": "Stacked column",
  "Chỉ số": "Metrics", "tối đa": "max", "Xoá biểu đồ": "Delete chart", "Xong": "Done", "Đã xoá biểu đồ": "Deleted chart", "Khôi phục": "Restore",
  "Trang": "Page", "Đã xoá trang": "Removed page", "khỏi báo cáo": "from the report", "Khôi phục trang": "Restore page", "Xoá trang": "Delete page",
  "Xoá trang này khỏi báo cáo (khôi phục lại được)": "Remove this page from the report (can be restored)",
  "Chuyển sang trái": "Move left", "Chuyển sang phải": "Move right", "Xoá thẻ": "Delete card", "Thêm thẻ KPI": "Add KPI card",
  "Thẻ trống": "Blank card", "Chỉ số khác": "Other KPIs", "tự nhập số và tên": "type your own value and name", "Thẻ đã xoá": "Deleted cards", "Sao chép từ": "Copy from",
  "File 4 trang tiếng Anh giống mẫu Dashboard Report của Xinyang Weekly Report: Match Making · Content · Group Posts & Links · Data 4 Pools.":
    "4-page English file in the same layout as the Xinyang Weekly Report Dashboard Report: Match Making · Content · Group Posts & Links · Data 4 Pools.",
  "Kỳ báo cáo": "Report period", "Từ ngày": "From", "Đến ngày": "To", "Tuần này": "This week", "Tuần trước": "Last week",
  "Nhận xét thêm (tuỳ chọn · mỗi dòng 1 ý · ghi tiếng Anh nếu gửi khách)": "Extra comments (optional · one point per line · write in English for the client)",
  "Additional activities (trang 1 · hoạt động ngoài hệ thống)": "Additional activities (page 1 · activities outside the system)",
  "Số liệu đọc trực tiếp từ Xinyang Odoo + SGT Odoo bằng tài khoản đang đăng nhập; mỗi thẻ so với kỳ trước (cùng độ dài) và cùng ngày tháng trước. Nhận xét tự lưu trên trình duyệt theo từng kỳ.":
    "Figures are read directly from Xinyang Odoo + SGT Odoo with the signed-in account; each card compares with the previous period (same length) and the same dates last month. Comments are saved in the browser for each period.",
  "Xem trước": "Preview", "Tải PDF": "Download PDF", "Báo cáo": "Report",
  "tuần đang chạy, số liệu tính đến hôm nay": "week in progress, figures up to today",
  "Hôm nay": "Today", "Hôm qua": "Yesterday", "hôm nay, số liệu tính đến lúc bấm xuất · so với hôm qua": "today, figures up to the moment of export · compared with yesterday",
  "so với hôm trước": "compared with the previous day",
  "Chọn đủ Từ ngày và Đến ngày.": "Choose both From and To dates.", "Đến ngày phải sau Từ ngày.": "The To date must be after the From date.",
  "Đang tạo báo cáo từ Odoo...": "Building the report from Odoo...", "Đang đọc số liệu Odoo và tạo PDF...": "Reading Odoo figures and building the PDF...",
  "Kỳ báo cáo tối đa 3 tháng.": "The report period is limited to 3 months.", "Ngày bắt đầu nằm trong tương lai.": "The start date is in the future.", "Bạn cần bật JavaScript để sử dụng bản đồ.": "You need to enable JavaScript to use the map.",
  /* Update 097: hộp chi tiết mẫu bản đồ cũ */
  "Thông tin Deal CRM": "CRM deal information",
  "Tên Deal": "Deal name",
  "Công ty / Contact": "Company / Contact",
  "Chưa liên kết Contact": "No linked Contact",
  "Điện thoại": "Phone",
  "Di động": "Mobile",
  "Trạng thái Deal hiện tại": "Current deal status",
  "Chưa xác định": "Not determined",
  "Tọa độ của Deal": "Deal coordinates",
  "Trạng thái định vị": "Geolocation status",
  "Chưa có trạng thái": "No status yet",
  "Cập nhật": "Updated",
  "Hồ sơ Contact liên kết": "Linked Contact profile",
  "Đang tải thông tin Contact…": "Loading Contact information…",
  "Tên doanh nghiệp": "Company name",
  "Mã số thuế": "Tax ID",
  "Thông tin liên hệ": "Contact information",
  "Hồ sơ doanh nghiệp": "Company profile",
  "Địa chỉ & tọa độ": "Address & coordinates",
  "Năm thành lập": "Founded year",
  "Loại": "Type",
  "Chưa chọn": "Not selected",
  "Mở Deal trên Odoo ↗": "Open deal in Odoo ↗",
  "Mở Contact trên Odoo ↗": "Open Contact in Odoo ↗",
  "Định vị trên bản đồ": "Locate on map",
  "Chưa có Deal CRM liên kết được xác minh.": "No verified linked CRM deal yet.",
  "Chọn Deal cần xem": "Choose the deal to view",
  "Công ty có nhiều Deal. Chọn Deal để xem đúng Stage hiện tại.": "This company has several deals. Choose a deal to see its current stage.",
  "Chưa xác minh": "Not verified",
  "Logo công ty": "Company logo",
  "Logo Contact": "Contact logo",
  "Danh sách hơn 100 Deal; mở Odoo để xem đầy đủ.": "More than 100 deals; open Odoo for the full list.",
  "Tọa độ lấy từ Contact Odoo. Chưa xác minh độ chính xác tại số nhà; không tự động ghi đè tọa độ.": "Coordinates come from the Odoo Contact. Street-level accuracy is not verified; coordinates are never overwritten automatically.",
  "Nguồn: Contact + CRM Odoo XINYANG · dữ liệu đọc trực tiếp khi mở chi tiết": "Source: XINYANG Odoo Contact + CRM · read live when the details open",
  "Nguồn: tọa độ lấy từ Contact (partner_latitude / partner_longitude) vì Deal chưa có tọa độ": "Source: coordinates taken from the Contact (partner_latitude / partner_longitude) because the deal has none",
  "Nguồn: crm.lead · x_yp_latitude / x_yp_longitude · không định vị lại địa chỉ": "Source: crm.lead · x_yp_latitude / x_yp_longitude · addresses are not re-geocoded",
  "Đang lấy hồ sơ Contact từ Odoo XINYANG…": "Loading the Contact profile from XINYANG Odoo…",
  "Đang mở thông tin Deal CRM…": "Opening CRM deal information…",
  "Không tải được Contact: ": "Could not load Contact: ",
  "Người liên hệ": "Contact person",
  "Một số ô trống ở Contact công ty nên được bù từ: ": "Some blank fields on the company Contact were filled from: ",
  "Contact con": "Child Contact",
  "Deal liên kết": "Linked deal",
  " (chỉ đọc, không ghi lại Odoo).": " (read-only, nothing is written back to Odoo).",
  "Tổng điểm": "Total points",
  "Tổng số điểm theo bộ lọc hiện tại (mọi stage)": "Total points under the current filters (all stages)",
};

const ZH_SRC = window.XINYANG_I18N_ZH || null;   // i18n_zh.js
const LANGS = ZH_SRC ? ["vi", "en", "zh"] : ["vi", "en"];
const LOCALES = {vi: "vi-VN", en: "en-US", zh: "zh-CN"};
const LABELS = {vi: "VI", en: "EN", zh: "中文"};
const NAMES = {vi: "Tiếng Việt", en: "English", zh: "中文"};
const ASCII_KEYS = [...new Set([...Object.keys(DICT), ...Object.keys(ZH_SRC?.dict || {})])].filter(k => !VN.test(k));

/* ------------------------------------------------------------ mẫu câu có biến (số, kỳ, tên) */
let tr; // khai báo trước để PATTERNS gọi đệ quy
const PATTERNS = [
  // Nhãn kỳ
  [/^Tuần (\d{1,2})\/(\d{4})$/, (_, w, y) => `Week ${w}/${y}`],
  [/^Tháng (\d{1,2})\/(\d{4})$/, (_, m, y) => `${MONTHS[+m - 1] || m} ${y}`],
  [/^Năm (\d{4})$/, (_, y) => `Year ${y}`],
  [/^T(\d{1,2})\/(\d{4})$/, (_, m, y) => `${MONTHS[+m - 1] || m} ${y}`],
  [/^T(\d{1,2})$/, (_, w) => `W${w}`],
  [/^(\d+) (tuần|tháng|năm)$/, (_, n, g) => `${n} ${GRAN_EN[g][+n === 1 ? 0 : 1]}`],
  // So sánh / bảng
  [/^(.+?) vs (.+)$/, (_, a, b) => `${tr(a)} vs ${tr(b)}`],
  [/^MM (.+)$/, (_, p) => `MM ${tr(p)}`],
  [/^Approved (.+)$/, (_, p) => `Approved ${tr(p)}`],
  [/^(\d+) thẻ KPI đang ẩn$/, (_, n) => `${n} KPI card${+n === 1 ? "" : "s"} hidden`],
  [/^(\d+) biểu đồ đang ẩn$/, (_, n) => `${n} chart${+n === 1 ? "" : "s"} hidden`],
  [/^(\d+)\. (.+)$/, (_, n, rest) => `${n}. ${tr(rest)}`],
  [/^Cập nhật (.+?)( \(cache\))?$/, (_, t, c) => `Updated ${t}${c || ""}`],
  [/^Xuất lúc (.+)$/, (_, t) => `Exported at ${t}`],
  [/^tổng (.+)$/, (_, v) => `total ${v}`],
  [/^Một số nguồn dữ liệu đọc lỗi: (.+)$/s, (_, e) => `Some data sources failed to load: ${tr(e)}`],
  // metrics.py
  [/^Kho ([A-Z0-9 _&-]+)$/, (_, k) => `${k} pipeline`],
  [/^Deal tiến lên (.+) trong kỳ$/, (_, s) => `Deals advancing to ${s} in the period`],
  [/^Deal từ (.+) chuyển vào Match Making \(mọi stage\)$/, (_, k) => `Deals from ${tr(k)} moved into Match Making (any stage)`],
  [/^(Chủ nhật|Thứ (\d)), (.+)$/, (_, w, n, d) => `${n ? ["", "", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][+n] : "Sun"}, ${d}`],
  [/^(\d+) ngày trước$/, (_, n) => `${n} days ago`],
  [/^([\d.,]+)% đạt$/, (_, v) => `${v}% passed`],
  [/^Deal được tạo mới ở (.+) \(tính cả deal đã chuyển đi \/ Lost\)$/, (_, k) => `Deals created in ${tr(k)} (including deals moved out / Lost)`],
  [/^Deal mới theo (.+?) qua các kỳ$/, (_, f) => `New deals by ${f} over periods`],
  [/^Deal mới theo ([^·]+)$/, (_, f) => `New deals by ${f}`],
  [/^(.+): ([\d.,]+) deal mới$/, (_, p, n) => `${tr(p)}: ${enNum(n)} new deals`],
  [/^Không tìm thấy project '(.+)' trong GB Submit \(SGT Odoo\)\.$/, (_, p) => `Project '${p}' not found in GB Submit (SGT Odoo).`],
  [/^Chưa đọc được GB Submit trên SGT Odoo: (.+)$/s, (_, e) => `Could not read GB Submit on SGT Odoo: ${tr(e)}`],
  // odoo.py
  [/^Sai tài khoản\/mật khẩu (.+) \(DB: (.+)\)\.$/, (_, l, d) => `Wrong username/password for ${l} (DB: ${d}).`],
  [/^(.+) phản hồi quá chậm \(timeout\)\.$/, (_, l) => `${l} responded too slowly (timeout).`],
  [/^Lỗi HTTP khi gọi (.+?): (.+)$/s, (_, l, e) => `HTTP error calling ${l}: ${e}`],
  [/^Không kết nối được (.+) tại (.+) sau (\d+) lần thử (.+)$/s, (_, l, u, n, e) => `Could not connect to ${l} at ${u} after ${n} attempts ${e}`],
  [/^(.+) trả HTTP (\d+)\.$/, (_, l, c) => `${l} returned HTTP ${c}.`],
  [/^(.+) không trả JSON\.$/, (_, l) => `${l} did not return JSON.`],
  [/^(.+) từ chối quyền đọc: (.+)$/s, (_, l, m) => `${l} denied read access: ${m}`],
  [/^Xinyang Odoo chưa có field (.+) — cần cập nhật CRM-005 (Update 047)\.$/, (_, f) => `Xinyang Odoo is missing field(s) ${f} — CRM-005 (Update 047) must be installed.`],
  [/^Ngày không hợp lệ \(YYYY-MM-DD\)\.$/, () => "Invalid date (YYYY-MM-DD)."],
  // map.js
  [/^Tất cả x_event \(([\d.,]+)\)$/, (_, n) => `All x_event (${enNum(n)})`],
  [/^([\d.,]+) bản ghi$/, (_, n) => `${enNum(n)} record${n === "1" ? "" : "s"}`],
  [/^([\d.,]+) có tọa độ \/ ([\d.,]+) khách hàng$/, (_, a, b) => `${enNum(a)} with coordinates / ${enNum(b)} customers`],
  [/^([\d.,]+) khách hàng phù hợp nhưng chưa có tọa độ\. Vào Odoo › Settings › Xinyang Map để chạy định vị\.$/,
    (_, n) => `${enNum(n)} matching customers have no coordinates yet. Coordinates come from the deal's x_yp_latitude / x_yp_longitude.`],
  [/^cache (\d+) phút$/, (_, n) => `cache ${n} min`],
  [/^([\d.,]+) Deal dùng tọa độ Contact$/, (_, n) => `${enNum(n)} deal${n === "1" ? "" : "s"} using the Contact's coordinates`],
  [/^([\d.,]+) Contact MM\/Approved từ bản đồ cũ$/, (_, n) => `${enNum(n)} MM/Approved Contact${n === "1" ? "" : "s"} from the old map`],
  [/^([\d.,]+) Contact tại khu vực này$/, (_, n) => `${enNum(n)} Contact${n === "1" ? "" : "s"} in this area`],
  [/^([\d.,]+) có tọa độ \/ ([\d.,]+) Contact$/, (_, a, b) => `${enNum(a)} with coordinates / ${enNum(b)} Contacts`],
  [/^Potential Map · Match Making ([\d.,]+) · Approved ([\d.,]+) · cả hai ([\d.,]+) · ([\d.,]+) deal · cùng dữ liệu bản đồ cũ · cache (\d+) phút$/,
    (_, a, b, c, d, m) => `Potential Map · Match Making ${enNum(a)} · Approved ${enNum(b)} · both ${enNum(c)} · ${enNum(d)} deals · same data as the old map · cache ${m} min`],
  [/^([\d.,]+) deal tại khu vực này$/, (_, n) => `${enNum(n)} deal${n === "1" ? "" : "s"} in this area`],
  [/^Xem thêm \(([\d.,]+)\)$/, (_, n) => `Show more (${enNum(n)})`],
  [/^([\d.,]+) deal gốc đã copy đang ẩn$/, (_, n) => `${enNum(n)} copied original deal${n === "1" ? "" : "s"} hidden`],
  // Xuất báo cáo (v4.7.0)
  [/^Trang (\d+)$/, (_, n) => `Page ${n}`],
  [/^VD: (.+)$/s, (_, x) => `E.g. ${x}`],
  [/^(\d+) ngày$/, (_, n) => `${n} day${n === "1" ? "" : "s"}`],
  [/^Đã tạo (.+) \(([\d.,]+) giây\)\.$/, (_, f, t) => `Created ${f} (${t} s).`],
  [/^Đã tạo file nhưng một số số liệu đọc lỗi: (.+)$/s, (_, e) => `File created, but some figures failed to load: ${e}`],
  [/^Chưa cài WeasyPrint trên server \((.+)\)\. Build lại bằng Dockerfile của bản (.+)\.$/s, (_, e, v) => `WeasyPrint is not installed on the server (${e}). Rebuild with the Dockerfile of version ${v}.`],
  [/^Đọc lúc (.+)$/, (_, t) => `Read at ${t}`],
  [/^Đã lưu nháp lúc (.+)$/, (_, t) => `Draft saved at ${t}`],
  [/^Đã xoá trang (.+) — bấm "Khôi phục trang" nếu cần lại$/, (_, t) => `Removed page ${t} — click "Restore page" to bring it back`],
  [/^Đã khôi phục trang (.+)$/, (_, t) => `Restored page ${t}`],
  [/^Tối đa (\d+) chỉ số trên 1 biểu đồ$/, (_, n) => `Up to ${n} metrics per chart`],
  [/^Trang (\d+) dài quá 1 tờ A4 — phần dưới vạch này sẽ sang trang mới trong PDF$/, (_, n) => `Page ${n} is longer than one A4 sheet — content below this line moves to a new PDF page`],
  [/^Số liệu Odoo đọc trong ([\d.,]+) giây · bấm vào chữ để sửa$/, (_, t) => `Odoo figures loaded in ${t} s · click any text to edit`],
  [/^Một số số liệu đọc lỗi: (.+)$/s, (_, e) => `Some figures failed to load: ${e}`],
  [/^Đang mở bản đã sửa \(lưu lúc (.+)\) · bấm "Lấy lại số liệu gốc" để đọc lại Odoo$/, (_, t) => `Showing your edited version (saved ${t}) · click "Reload original figures" to re-read Odoo`],
  [/^Báo cáo: (.+)$/s, (_, x) => `Report: ${x}`],
  [/^Ngày (\d\d\/\d\d\/\d{4})$/, (_, d) => `Day ${d}`],
  [/^Lỗi: (.+)$/s, (_, e) => `Error: ${tr(e)}`],
  // Câu tăng/giảm (tooltip): "Tăng 12 (+31,9%)", "Giảm 3 điểm %", "Tăng 5 (kỳ trước = 0)", "Không đổi (0%)"
  [/^(Tăng|Giảm) ([\d.,]+) điểm %$/, (_, w, n) => `${w === "Tăng" ? "Up" : "Down"} ${n} pts`],
  [/^(Tăng|Giảm) ([\d.,]+) \(kỳ trước = 0\)$/, (_, w, n) => `${w === "Tăng" ? "Up" : "Down"} ${enNum(n)} (previous period = 0)`],
  [/^(Tăng|Giảm) ([\d.,]+) \(([+−-])([\d.,]+)%\)$/, (_, w, n, sg, p) => `${w === "Tăng" ? "Up" : "Down"} ${enNum(n)} (${sg}${p.replace(",", ".")}%)`],
  [/^Không đổi( \(0%\))?$/, (_, z) => `No change${z || ""}`],
  // delta: "+12 Mới", "+12 (Mới)", "▲ 3,5 điểm"
  [/^(.*?)\(Mới\)$/, (_, a) => `${a}(New)`],
  [/^(.*?\S )?Mới$/, (_, a) => `${a || ""}New`],
  [/^(.*\d) điểm$/, (_, a) => `${a} pts`],
  [/^(.*) \| (.+)$/, (_, a, b) => `${tr(a)} | ${tr(b)}`],
];

/* ------------------------------------------------------------ bộ dịch chuỗi (dùng chung cho EN và ZH) */
const missingSet = new Set();
function translateWith(L, s) {
  if (!s || !needs(s)) return s;
  if (Object.prototype.hasOwnProperty.call(L.dict, s)) return L.dict[s];
  for (const [re, fn] of L.patterns) { const m = s.match(re); if (m) return fn(...m); }
  const t = L.t;
  // Tách theo " · " rồi dịch từng đoạn
  if (s.includes("·")) {
    const parts = s.split(/(\s*·\s*)/);
    if (parts.length > 1) return parts.map((p, i) => i % 2 ? p : t(p)).join("");
  }
  // Dấu hai chấm / ngoặc ở cuối: "Đang tồn ở 4 kho:" → dịch phần trước
  let m = s.match(/^(.+?)(\s*:)$/s); if (m) { const x = t(m[1]); if (x !== m[1]) return x + m[2]; }
  m = s.match(/^\((.+)\)$/s); if (m) { const x = t(m[1]); if (x !== m[1]) return `(${x})`; }
  // Ký hiệu ở đầu/cuối: "⚙ Tuỳ chỉnh", "↻ Làm mới", "Mở Deal… ↗"
  m = s.match(/^([^\p{L}\p{N}(]+)(.*?)([^\p{L}\p{N}).%]*)$/su);
  if (m && (m[1] || m[3]) && m[2]) { const x = t(m[2]); if (x !== m[2]) return m[1] + x + m[3]; }
  m = s.match(/^(.*?\p{L})([^\p{L}\p{N}).%]+)$/su);
  if (m && m[2]) { const x = t(m[1]); if (x !== m[1]) return x + m[2]; }
  // Tiếng Trung chưa có bản dịch → dùng bản tiếng Anh thay vì để tiếng Việt
  if (L.fallback) { const f = L.fallback(s); if (f !== s) { L.missing.add(s); return f; } }
  if (VN.test(s)) L.missing.add(s);
  return s;
}
function makeTranslator(L) {
  const cache = new Map();
  return function (s) {
    if (s === null || s === undefined) return s;
    s = String(s);
    if (cache.has(s)) return cache.get(s);
    const lead = s.match(/^\s*/)[0], trail = s.slice(lead.length).match(/\s*$/)[0];
    const core = s.slice(lead.length, s.length - trail.length);
    const out = core ? lead + translateWith(L, core) + trail : s;
    if (cache.size > 5000) cache.clear();
    cache.set(s, out);
    return out;
  };
}
const EN = {dict: DICT, patterns: PATTERNS, missing: missingSet};
tr = EN.t = makeTranslator(EN);
let ZH = null;
if (ZH_SRC) {
  ZH = {dict: ZH_SRC.dict, missing: new Set(), fallback: s => tr(s)};
  ZH.t = makeTranslator(ZH);
  ZH.patterns = ZH_SRC.patterns(ZH.t, enNum);
}
// Dịch theo ngôn ngữ đang chọn (vi = giữ nguyên)
const T = s => lang === "zh" && ZH ? ZH.t(s) : lang === "en" ? tr(s) : s;

/* ------------------------------------------------------------ khối HTML dài (Chú giải KPI) */
const BLOCKS_EN = {
  legend: `
  <h2>KPI Glossary</h2>
  <p><b>How comparison works:</b> choose Week / Month / Year. KPI cards show the figure for the viewing period and the % increase/decrease versus the previous period. If the viewing period has not ended yet, the previous period is cut to the same number of days (e.g. Monday→Wednesday this week vs Monday→Wednesday last week) for a fair comparison.</p>
  <h3>Match Making (Xinyang Odoo · History stage change)</h3>
  <p><b>1–6. Opportunity → Approved Match Making:</b> number of deals <u>entering</u> that stage in the period, taken from the History stage change table. Only real forward moves count: newly created deals, deals moved in from the 4 pipelines, or deals moving up from a lower stage. <b>Not counted:</b> revived deals (sent back to Opportunity), deals pulled back to an earlier stage and deals shifted in bulk when a stage is deleted/changed. Figures for past periods stay fixed; a deal entering the same stage several times on one day counts once.</p>
  <p><b>1. Opportunity</b> = deals created in the period + deals moved from the 4 pipelines into Match Making. <b>6. Approved Match Making</b> = the Won stage of the Match Making pipeline (approved MM).</p>
  <p>The small rate next to the number (cards 2–6) = stage count / Opportunity count in the same period.</p>
  <p><b>MM leaderboard by staff:</b> number of deals each staff member moved into stage 5.Match Making in the period (forward moves only, same as card 5), sorted from most to least; with Approved MM in the period, comparison with the previous period and MM counts for recent weeks/months/years. Staff = the deal owner (Salesperson) at the time of the stage change.</p>
  <h3>Content (SGT Odoo · GB Submit · project XINYANG)</h3>
  <p><b>7. Content submitted:</b> all content sent to project XINYANG, by content creation date. <b>8. Approved, not yet posted:</b> content in Approved status. <b>9. Used for posting:</b> content in Archived status (used). Cards 8 and 9 are counted on content submitted in the same period.</p>
  <h3>Group posts &amp; Links (SGT Odoo · Publishing History)</h3>
  <p><b>10. Facebook group posts</b> = Total Published = Passed links + Failed links + Uncheck. <b>11. Passed links</b> = Approved Links (posted successfully, check OK). <b>12. Failed links</b> = Not Approved Links (blocked/deleted, no post ID, timeout). <b>Uncheck</b> = newly posted links not checked yet. The formula matches the GB Submit Summary wizard on SGT.</p>
  <h3>4-pipeline data → Match Making (Xinyang Odoo)</h3>
  <p><b>13.</b> Number of deals from the 4 pipelines (Inbound Pool, Outbound Data, Inbound GB, Outbound Hunter) moved into the MATCH MAKING pipeline in the period, into any stage (Opportunity or others). Both transfer modes count: <b>move</b> (the deal leaves the pipeline) and <b>copy</b> (the original stays, Odoo creates a new deal in Match Making). The chart splits by pipeline; "Currently in" = deals still sitting in the 4 pipelines and not yet at the Approved stage.</p>
  <p><b>14. New data in the 4 pipelines:</b> number of deals <u>created</u> in the 4 pipelines in the period, split by pipeline (read from stage-change History: the "created" record whose stage belongs to the pipeline). Deals later moved to Match Making or Lost still count on their creation day. The card also shows <b>Today</b> (when viewing the current period) and <b>Average / day</b>; the "New data per day" chart shows the most recent days up to the end of the period being viewed (weekly view: 14 days to compare with last week; monthly: the whole month; max 31 days); Average / day only counts days in the period being viewed. Same formula as "New data" in the Dashboard Report.</p>
  <h3>Customer Map (Xinyang Odoo · addon CRM-005)</h3>
  <p>Each point is one deal with <b>x_address</b> and coordinates <b>x_latitude / x_longitude</b>. Coordinates are geocoded by the CRM-005 addon using Gemini (usually accurate to ward/district) or entered manually on the Deal. <b>Points</b> are clustered, the number in a cluster = customer count; <b>Density</b> = heatmap. Points and clusters are coloured by Stage (grey = new → red = in Match Making, green = Approved), switchable to Salesperson / Pipeline; clusters are split by deal count. Original deals already copied to another pipeline are hidden so that 1 customer = 1 point. Filter by Pipeline, Stage, x_expo, x_event, province/district, Salesperson, Tags. Data is read with the signed-in account and cached for 5 minutes; click "Reload Odoo" to get fresh numbers immediately.</p>
  <h3>Data sources: Tag &amp; Source (Xinyang Odoo)</h3>
  <p>Number of deals <u>created</u> in the period across all pipelines (including Lost/archived deals so past figures do not change; copies made when transferring between pipelines are <b>not</b> counted, as they are not new data), split by the deal's <b>Tags</b> and <b>Source</b> fields. A deal with several tags is counted under each tag. Charts over periods show the top 7 tags/sources, the rest is grouped into "Other"; deals with nothing filled in are grouped into "No tag" / "No source".</p>
  <h3>Comparing this period with the previous one on charts</h3>
  <p>Every chart shows the increase/decrease and % versus the previous period (e.g. "+12 (▲ 31.9%)") (this week vs last week, this month vs last month…). Charts over periods: a strip of figures right under the title for each data series. Charts for the viewing period: ▲▼ figures next to each bar / legend item. Table view adds a % change column. Hover over any column to see the % versus the period right before it. A period in progress is compared with the same number of days of the previous period; percentages (passed links) are compared in percentage points.</p>
  <h3>Show / hide KPI cards</h3>
  <p>Hover over a card and click ✕ in the corner to hide it; or open <b>⚙ Customize</b> → KPI cards to toggle each card. Saved in the browser.</p>
  <h3>Ordering</h3>
  <p>Use the ▲▼ buttons at the corner of each group to move the whole group up/down; the ▲▼ buttons on each chart change its position within the group. Or open <b>⚙ Customize</b> to arrange everything in one place. "Restore defaults" returns to the original order.</p>
  <h3>Charts</h3>
  <p>Each chart can change type (column, stacked column, line, area, horizontal bar, stacked horizontal bar, pie, donut, table), width, and be shown/hidden; click a legend item to show/hide that data series. Customizations are saved in the browser. Click a KPI card to jump to its chart.</p>
  <p><b>Access:</b> every query uses the signed-in Odoo account, so Odoo access rights and record rules still apply.</p>`,
};

const BLOCKS = {en: BLOCKS_EN, zh: ZH_SRC?.blocks || BLOCKS_EN};

/* ------------------------------------------------------------ dịch DOM */
const ATTRS = ["title", "placeholder", "aria-label"];
const textOrig = new WeakMap();           // text node -> {orig, out}
const attrOrig = new WeakMap();           // element -> {attr: {orig, out}}
const blockOrig = new WeakMap();          // element -> html gốc
let lang = "vi", applying = false, observer = null;
const listeners = [];

const skip = el => !el || !!el.closest?.("script,style,noscript,textarea,[data-no-i18n],.status-pre");
function doText(node) {
  const cur = node.nodeValue, rec = textOrig.get(node);
  const orig = rec && cur === rec.out ? rec.orig : cur;
  if (!needs(orig)) { if (rec) textOrig.delete(node); return; }
  const out = lang !== "vi" ? T(orig) : orig;
  textOrig.set(node, {orig, out});
  if (out !== cur) {
    const opt = node.parentNode;
    // <option> không có value: giữ value gốc để bộ lọc vẫn so đúng dữ liệu
    if (opt && opt.nodeName === "OPTION" && !opt.hasAttribute("value")) opt.setAttribute("value", orig.trim());
    node.nodeValue = out;
  }
}
function doAttrs(el) {
  let recs = attrOrig.get(el);
  for (const a of ATTRS) {
    if (!el.hasAttribute(a)) continue;
    const cur = el.getAttribute(a), rec = recs?.[a];
    const orig = rec && cur === rec.out ? rec.orig : cur;
    if (!VN.test(orig)) continue;
    const out = lang !== "vi" ? T(orig) : orig;
    if (!recs) attrOrig.set(el, recs = {});
    recs[a] = {orig, out};
    if (out !== cur) el.setAttribute(a, out);
  }
}
function doBlock(el) {
  const key = el.getAttribute("data-i18n-block"); if (!BLOCKS_EN[key]) return;
  if (lang !== "vi") { if (!blockOrig.has(el)) blockOrig.set(el, el.innerHTML); el.innerHTML = (BLOCKS[lang] || BLOCKS_EN)[key] || BLOCKS_EN[key]; }
  else if (blockOrig.has(el)) { el.innerHTML = blockOrig.get(el); blockOrig.delete(el); }
}
function walk(root) {
  if (!root) return;
  if (root.nodeType === 3) { if (!skip(root.parentElement)) doText(root); return; }
  if (root.nodeType !== 1 && root.nodeType !== 9) return;
  if (root.nodeType === 1) {
    if (skip(root)) return;
    if (root.hasAttribute("data-i18n-block")) { doBlock(root); return; }
    doAttrs(root);
  }
  const it = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode: n => n.nodeType === 1 && (skip(n) || n.hasAttribute("data-i18n-block")) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
  });
  let n; while ((n = it.nextNode())) n.nodeType === 3 ? doText(n) : doAttrs(n);
  if (root.querySelectorAll) root.querySelectorAll("[data-i18n-block]").forEach(b => { if (!skip(b.parentElement || b)) doBlock(b); });
}
function apply(root) {
  applying = true;
  try { walk(root || document.body); } finally { observer && observer.takeRecords(); applying = false; }
}
function startObserver() {
  if (observer || !window.MutationObserver) return;
  observer = new MutationObserver(muts => {
    if (applying) return;
    applying = true;
    try {
      for (const m of muts) {
        if (m.type === "childList") m.addedNodes.forEach(walk);
        else if (m.type === "characterData") { if (!skip(m.target.parentElement)) doText(m.target); }
        else if (m.type === "attributes" && !skip(m.target)) doAttrs(m.target);
      }
    } finally { observer.takeRecords(); applying = false; }
  });
  observer.observe(document.documentElement, {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS});
}

/* ------------------------------------------------------------ dịch payload API (canvas, CSV) */
const PAYLOAD_KEYS = new Set(["title", "subtitle", "label", "labels", "name", "note", "error", "errors", "nav_label", "full_labels", "periods", "full_periods"]);
function payload(p) {
  if (lang === "vi" || !p) return p;
  const walkVal = (v, k) => {
    if (Array.isArray(v)) return v.map(x => walkVal(x, k));
    if (v && typeof v === "object") { const o = {}; for (const kk in v) o[kk] = walkVal(v[kk], kk); return o; }
    return typeof v === "string" && PAYLOAD_KEYS.has(k) ? T(v) : v;
  };
  return walkVal(p, "");
}

/* ------------------------------------------------------------ đổi ngôn ngữ */
function updateButtons() {
  // Nút cũ (1 nút bấm vòng qua các ngôn ngữ)
  document.querySelectorAll("[data-lang-toggle]").forEach(b => {
    const next = LANGS[(LANGS.indexOf(lang) + 1) % LANGS.length];
    b.innerHTML = `&#127760; ${NAMES[next]}`;
    b.title = NAMES[next];
    b.classList.toggle("active", lang !== "vi");
  });
  // Nút chọn ngôn ngữ: VI | EN | 中文
  document.querySelectorAll("[data-lang-switch]").forEach(box => {
    if (!box.dataset.built) {
      box.innerHTML = '<span class="lang-globe" aria-hidden="true">&#127760;</span>' +
        LANGS.map(l => `<button type="button" data-lang="${l}" title="${NAMES[l]}" lang="${l === "zh" ? "zh-CN" : l}">${LABELS[l]}</button>`).join("");
      box.dataset.built = "1";
    }
    box.querySelectorAll("[data-lang]").forEach(b => {
      const on = b.dataset.lang === lang;
      b.classList.toggle("active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
  });
}
const htmlLang = l => l === "zh" ? "zh-CN" : l;
function setLang(next, opts = {}) {
  next = LANGS.includes(next) ? next : "vi";
  const changed = next !== lang;
  lang = next;
  if (!opts.noSave) { try { localStorage.setItem(KEY, lang); } catch {} }
  document.documentElement.lang = htmlLang(lang);
  if (document.title) document.title = lang !== "vi" ? T(document.__origTitle ??= document.title) : (document.__origTitle ?? document.title);
  if (document.body) { apply(document.body); updateButtons(); }
  // Đồng bộ iframe bản đồ (cùng origin)
  document.querySelectorAll("iframe").forEach(f => { try { f.contentWindow?.XINYANG_I18N?.setLang(lang, {noSave: true}); } catch {} });
  if (changed) listeners.forEach(fn => { try { fn(lang); } catch (e) { console.error(e); } });
}
function initialLang() {
  const q = new URLSearchParams(location.search).get("lang");
  if (LANGS.includes(q)) return q;
  try { const v = localStorage.getItem(KEY); return LANGS.includes(v) ? v : "vi"; } catch { return "vi"; }
}

window.XINYANG_I18N = {
  t: s => T(s),
  payload, setLang,
  get lang() { return lang; },
  languages: LANGS,
  locale: () => LOCALES[lang] || "vi-VN",
  toggle: () => setLang(LANGS[(LANGS.indexOf(lang) + 1) % LANGS.length]),
  onChange: fn => listeners.push(fn),
  missing: (l = "en") => [...(l === "zh" ? (ZH?.missing || []) : missingSet)],
  refresh: () => apply(document.body),
};

lang = initialLang();
document.documentElement.lang = htmlLang(lang);
const boot = () => {
  document.addEventListener("click", e => {
    const pick = e.target.closest?.("[data-lang-switch] [data-lang]");
    if (pick) { e.preventDefault(); setLang(pick.dataset.lang); return; }
    const b = e.target.closest?.("[data-lang-toggle]"); if (b) { e.preventDefault(); window.XINYANG_I18N.toggle(); }
  });
  // iframe nhận đổi ngôn ngữ từ tab khác / cửa sổ cha qua localStorage
  window.addEventListener("storage", e => { if (e.key === KEY) setLang(e.newValue, {noSave: true}); });
  if (lang !== "vi") { document.__origTitle = document.title; document.title = T(document.title); apply(document.body); }
  updateButtons();
  startObserver();
};
document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", boot) : boot();
})();
