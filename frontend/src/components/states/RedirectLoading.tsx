export default function RedirectLoading({ message = "Đang xử lý... Vui lòng đợi trong giây lát." }) {
  return (
    <div className="w-screen h-screen overflow-hidden flex flex-col items-center justify-center bg-[#e6f4ea] font-sans select-none">
      {/* Hình tròn quay quay giữa màn hình */}
      <div className="relative flex items-center justify-center mb-8">
        <div className="absolute w-24 h-24 bg-[#3b7a52]/20 rounded-full blur-xl animate-pulse"></div>
        
        <div className="w-20 h-20 border-2 border-dashed border-[#3b7a52]/30 rounded-full animate-[spin_5s_linear_infinite]"></div>
        
        <div className="absolute w-14 h-14 border-4 border-transparent border-t-[#3b7a52] border-r-[#428a5d] rounded-full animate-spin"></div>
        
        <div className="absolute w-5 h-5 bg-[#2e4a38] rounded-full flex items-center justify-center">
          <div className="w-full h-full bg-[#3b7a52] rounded-full animate-ping opacity-75"></div>
        </div>
      </div>
      
      {/* Khối hiển thị thông báo */}
      <div className="text-center space-y-2 px-4">
        <h2 className="text-[16px] font-semibold text-[#2e4a38] tracking-wide animate-pulse">
          {message}
        </h2>
        {/* <p className="text-[12px] text-[#5c7a65] font-medium opacity-70">
          Hệ thống đang điều hướng, vui lòng không đóng trình duyệt
        </p> */}
      </div>

    </div>
  );
}