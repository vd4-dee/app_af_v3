def get_report_url(report_type=None):
    # Define your report URLs here
    report_urls = {
        "FAF001 -   Báo cáo bán hàng chi tiết rút gọn": 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF001.aspx',
        "FAF002 - Báo cáo bán hàng chi tiết cắt liều": 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF002.aspx',
        "FAF003 - Báo cáo nhập khác xuất khác": 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF003.aspx',
        "FAF004N - Báo cáo luân chuyển nội bộ (Imports)": 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF004.aspx',
        "FAF004X - Báo cáo luân chuyển nội bộ (Exports)": 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF004.aspx',
        "FAF005 - Báo cáo nhập hàng": 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF005.aspx',
        "FAF006 - Báo cáo trả hàng NCC": 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF006.aspx',
        "FAF028 - Báo cáo chi tiết nhập xuất": 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF028.aspx',
        "FAF030 - Báo cáo nhập xuất tồn": 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF030.aspx',
        "PHAR157 - Báo Cáo Thông Tin Shop Mở Bán": 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHAR157.aspx',
        "FAF010 - Báo Cáo Quỹ": 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF010.aspx'
    }
    if report_type:
        # Case-insensitive and whitespace-insensitive lookup
        normalized = report_type.strip().lower()
        for key, url in report_urls.items():
            if key.strip().lower() == normalized:
                return url
        return None
    return report_urls

link001 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF001.aspx'
link002 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF002.aspx'
link003 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF003.aspx'
link004 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF004.aspx'
link005 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF005.aspx'
link006 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF006.aspx'
link010 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF010.aspx'
link028 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF028.aspx'
link030 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF030.aspx'
link033 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF033.aspx'
link043 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHAR043.aspx'
link157 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHAR157.aspx'
link075 = 'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHAR075.aspx'