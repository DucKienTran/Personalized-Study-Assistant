export function formatDate(
    date?: string,
    locale = "vi-VN"
) {
    if (!date) return "";

    return new Date(date).toLocaleDateString(locale);
}

export function formatDateTime(
    date?: string,
    locale = "vi-VN"
) {
    if (!date) return "";

    return new Date(date).toLocaleString(locale);
}

export function formatRelative(
    date?: string
) {
    if (!date) return "";

    const diff = Date.now() - new Date(date).getTime();

    const minute = Math.floor(diff / 60000);

    if (minute < 1) return "Vừa xong";

    if (minute < 60)
        return `${minute} phút trước`;

    const hour = Math.floor(minute / 60);

    if (hour < 24)
        return `${hour} giờ trước`;

    const day = Math.floor(hour / 24);

    if (day < 30)
        return `${day} ngày trước`;

    const month = Math.floor(day / 30);

    if (month < 12)
        return `${month} tháng trước`;

    const year = Math.floor(month / 12);

    return `${year} năm trước`;
}