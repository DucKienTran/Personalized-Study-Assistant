export default function WorkspaceSkeleton() {
    return (
        <div className="max-w-5xl mx-auto space-y-8 pt-4 w-full">
            {/* Skeleton Lời chào */}
            <div className="space-y-3">
                <div className="h-8 bg-gray-200 rounded-md w-64 animate-pulse"></div>
                <div className="h-4 bg-gray-100 rounded-md w-48 animate-pulse"></div>
            </div>

            {/* Skeleton 4 ô tính năng */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[1, 2, 3, 4].map((item) => (
                    <div key={item} className="bg-white border border-gray-100 rounded-2xl p-5 flex flex-col justify-between h-[180px]">
                        <div>
                            <div className="w-12 h-12 bg-gray-100 rounded-xl mb-4 animate-pulse"></div>
                            <div className="h-5 bg-gray-200 rounded-md w-3/4 mb-3 animate-pulse"></div>
                            <div className="space-y-2">
                                <div className="h-3 bg-gray-100 rounded-md w-full animate-pulse"></div>
                                <div className="h-3 bg-gray-100 rounded-md w-5/6 animate-pulse"></div>
                            </div>
                        </div>
                        <div className="mt-6 pt-3 border-t border-gray-50 flex justify-end">
                            <div className="h-4 bg-gray-100 rounded-md w-16 animate-pulse"></div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}