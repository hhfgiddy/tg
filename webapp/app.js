const tg = window.Telegram?.WebApp || null;


/* =========================================
   TELEGRAM MINI APP
========================================= */

if (tg) {
    tg.ready();
    tg.expand();

    try {
        tg.setHeaderColor("#080b16");
        tg.setBackgroundColor("#080b16");
    } catch (error) {
        console.log("Telegram WebApp settings error", error);
    }
}


/* =========================================
   ELEMENTS
========================================= */

const pages = {
    home: document.getElementById("home-page"),
    create: document.getElementById("create-page"),
    "my-contests": document.getElementById("my-contests-page"),
    profile: document.getElementById("profile-page"),
    help: document.getElementById("help-page"),
};

const contestForm = document.getElementById("contest-form");

const targetChannelInput =
    document.getElementById("target-channel-input");

const targetChannelResult =
    document.getElementById("target-channel-result");

const postText =
    document.getElementById("post-text");

const postImageInput =
    document.getElementById("post-image-input");

const postImagePreview =
    document.getElementById("post-image-preview");

const imagePreviewBox =
    document.getElementById("image-preview-box");

const removeImageButton =
    document.getElementById("remove-image");

const requiredChannelInput =
    document.getElementById("required-channel-input");

const addRequiredChannelButton =
    document.getElementById("add-required-channel");

const requiredChannelList =
    document.getElementById("required-channel-list");

const endTypeTime =
    document.getElementById("end-type-time");

const endTypeLimit =
    document.getElementById("end-type-limit");

const endTimeField =
    document.getElementById("end-time-field");

const participantLimitField =
    document.getElementById("participant-limit-field");

const endAt =
    document.getElementById("end-at");

const participantLimit =
    document.getElementById("participant-limit");

const winnersCount =
    document.getElementById("winners-count");

const buttonText =
    document.getElementById("button-text");

const startNowButton =
    document.getElementById("start-now-button");

const startScheduledButton =
    document.getElementById("start-scheduled-button");

const startTimeField =
    document.getElementById("start-time-field");

const startAt =
    document.getElementById("start-at");

const previewModal =
    document.getElementById("preview-modal");

const previewContent =
    document.getElementById("preview-content");

const closePreviewButton =
    document.getElementById("close-preview");

const editPreviewButton =
    document.getElementById("edit-preview");

const confirmContestButton =
    document.getElementById("confirm-contest");

const toast =
    document.getElementById("toast");

const myContestsList =
    document.getElementById("my-contests-list");

const myContestsEmpty =
    document.getElementById("my-contests-empty");

const profileAvatar =
    document.getElementById("profile-avatar");

const profileAvatarImage =
    document.getElementById("profile-avatar-image");

const profileName =
    document.getElementById("profile-name");

const profileUsername =
    document.getElementById("profile-username");


/* =========================================
   STATE
========================================= */

let currentPage = "home";

let currentEndType = "time";

let currentStartMode = "now";

let selectedImageData = "";

let resolvedTargetChannel = null;

let requiredChannels = [];

let previewContestData = null;

let toastTimer = null;

let contests = loadContests();


/* =========================================
   ICONS
========================================= */

function iconSvg(name) {

    const icons = {

        channel: `
            <svg viewBox="0 0 24 24">
                <path d="M21 4.5 17.8 19c-.24 1.03-.84 1.29-1.7.8l-4.7-3.46-2.27 2.18c-.25.25-.46.46-.94.46l.34-4.78 8.7-7.86c.38-.34-.08-.53-.59-.19L6.01 12.82l-4.62-1.45c-1-.31-1.02-1 .21-1.48L19.65 3.1C20.56 2.77 21.36 3.3 21 4.5Z"/>
            </svg>
        `,

        users: `
            <svg viewBox="0 0 24 24">
                <path d="M16 20v-1.5a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4V20"/>
                <circle cx="9.5" cy="7" r="3"/>
                <path d="M17 11a3 3 0 1 0 0-6"/>
                <path d="M21 20v-1.5a4 4 0 0 0-3-3.87"/>
            </svg>
        `,

        close: `
            <svg viewBox="0 0 24 24">
                <path d="m6 6 12 12M18 6 6 18"/>
            </svg>
        `,

        check: `
            <svg viewBox="0 0 24 24">
                <path d="m5 12 4 4L19 6"/>
            </svg>
        `,

        clock: `
            <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="8"/>
                <path d="M12 8v4l3 2"/>
            </svg>
        `,

        trophy: `
            <svg viewBox="0 0 24 24">
                <path d="M8 4h8v5a4 4 0 0 1-8 0V4Z"/>
                <path d="M8 6H5v2a3 3 0 0 0 3 3M16 6h3v2a3 3 0 0 1-3 3"/>
                <path d="M12 13v4M8 20h8"/>
            </svg>
        `,

    };

    return icons[name] || "";
}


/* =========================================
   TELEGRAM USER
========================================= */

function getTelegramUser() {

    if (
        tg &&
        tg.initDataUnsafe &&
        tg.initDataUnsafe.user
    ) {
        return tg.initDataUnsafe.user;
    }

    return {
        id: 0,
        first_name: "Foydalanuvchi",
        last_name: "",
        username: "",
        photo_url: "",
    };
}


/* =========================================
   NAVIGATION
========================================= */

function showPage(pageName) {

    if (!pages[pageName]) {
        return;
    }

    Object.entries(pages).forEach(
        ([name, page]) => {
            page.hidden = name !== pageName;
        }
    );

    currentPage = pageName;

    document
        .querySelectorAll("[data-page]")
        .forEach((button) => {

            if (
                button.classList.contains("nav-item")
            ) {
                button.classList.toggle(
                    "active",
                    button.dataset.page === pageName
                );
            }

        });

    if (pageName === "my-contests") {
        renderMyContests();
    }

    if (tg) {

        try {

            if (pageName === "home") {
                tg.BackButton.hide();
            } else {
                tg.BackButton.show();
            }

        } catch (error) {
            console.log(error);
        }
    }

    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });

    haptic("light");
}


/* =========================================
   NAVIGATION EVENTS
========================================= */

document
    .querySelectorAll("[data-page]")
    .forEach((button) => {

        button.addEventListener("click", () => {

            const pageName =
                button.dataset.page;

            if (pageName) {
                showPage(pageName);
            }

        });

    });


if (tg) {

    try {

        tg.BackButton.onClick(() => {

            if (currentPage !== "home") {
                showPage("home");
            } else {
                tg.BackButton.hide();
            }

        });

    } catch (error) {
        console.log(error);
    }
}


/* =========================================
   PROFILE
========================================= */

function loadProfile() {

    const user = getTelegramUser();

    const firstName =
        user.first_name || "Foydalanuvchi";

    const lastName =
        user.last_name || "";

    const fullName =
        `${firstName} ${lastName}`.trim();

    profileName.textContent =
        fullName;

    profileUsername.textContent =
        user.username
            ? `@${user.username}`
            : "Telegram foydalanuvchisi";

    profileAvatar.textContent =
        firstName
            .charAt(0)
            .toUpperCase();

    if (user.photo_url) {

        profileAvatarImage.src =
            user.photo_url;

        profileAvatarImage.classList.remove(
            "hidden"
        );

        profileAvatar.classList.add(
            "hidden"
        );

    } else {

        profileAvatarImage.classList.add(
            "hidden"
        );

        profileAvatar.classList.remove(
            "hidden"
        );

    }
}


/* =========================================
   HAPTIC
========================================= */

function haptic(type = "light") {

    try {

        if (
            tg &&
            tg.HapticFeedback
        ) {

            tg.HapticFeedback.impactOccurred(
                type
            );

        }

    } catch (error) {
        console.log(error);
    }
}


/* =========================================
   TOAST
========================================= */

function showToast(message) {

    clearTimeout(toastTimer);

    toast.textContent = message;

    toast.classList.add("show");

    toastTimer = setTimeout(() => {

        toast.classList.remove("show");

    }, 2600);
}


/* =========================================
   ESCAPE HTML
========================================= */

function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


/* =========================================
   TELEGRAM TARGET NORMALIZER
========================================= */

function normalizeTelegramTarget(value) {

    if (!value) {
        return null;
    }

    let raw =
        String(value)
            .trim();

    if (!raw) {
        return null;
    }


    /*
        HTTPS:
        https://t.me/username
        http://t.me/username
    */

    if (
        /^https?:\/\/t\.me\//i.test(raw)
    ) {

        try {

            const url =
                new URL(raw);

            let username =
                url.pathname
                    .replace(/^\/+/, "")
                    .replace(/\/+$/, "");

            if (
                username &&
                /^[A-Za-z0-9_]{5,32}$/.test(
                    username
                )
            ) {

                return {
                    type: "username",
                    username,
                    key:
                        `username:${username.toLowerCase()}`,
                    original: raw,
                };

            }

        } catch (error) {
            return null;
        }

    }


    /*
        @username
        username
    */

    if (
        /^@?[A-Za-z0-9_]{5,32}$/.test(raw)
    ) {

        const username =
            raw.replace(/^@/, "");

        return {
            type: "username",
            username,
            key:
                `username:${username.toLowerCase()}`,
            original: raw,
        };

    }


    /*
        Numeric Telegram ID
    */

    if (
        /^-?\d+$/.test(raw)
    ) {

        return {
            type: "id",
            id: raw,
            key: `id:${raw}`,
            original: raw,
        };

    }

    return null;
}


/* =========================================
   DEMO RESOLVER
========================================= */

function resolveTelegramTarget(value) {

    const normalized =
        normalizeTelegramTarget(value);

    if (!normalized) {
        return null;
    }


    /*
        Bu DEMO resolver.

        Real backend ulanganda Telegram API
        orqali haqiqiy kanal nomi / username
        resolve qilinadi.
    */

    if (
        normalized.type === "username"
    ) {

        const username =
            normalized.username;

        return {
            ...normalized,

            title:
                `@${username}`,

            username:
                `@${username}`,

            display:
                `@${username}`,
        };

    }


    return {
        ...normalized,

        title:
            `Telegram ID ${normalized.id}`,

        username:
            `ID: ${normalized.id}`,

        display:
            `Telegram ID ${normalized.id}`,
    };
}


/* =========================================
   TARGET CHANNEL RESOLUTION
========================================= */

function renderTargetChannelResult() {

    if (!resolvedTargetChannel) {

        targetChannelResult.classList.add(
            "hidden"
        );

        targetChannelResult.innerHTML = "";

        return;
    }


    targetChannelResult.classList.remove(
        "hidden"
    );


    targetChannelResult.innerHTML = `

        <div class="resolved-result-icon">
            ${iconSvg("channel")}
        </div>

        <div>
            <strong>
                ${escapeHtml(
                    resolvedTargetChannel.title
                )}
            </strong>

            <span>
                ${escapeHtml(
                    resolvedTargetChannel.username
                )}
            </span>
        </div>

    `;
}


function resolveTargetChannel() {

    const value =
        targetChannelInput.value;

    if (!value.trim()) {

        resolvedTargetChannel = null;

        renderTargetChannelResult();

        return;
    }


    const resolved =
        resolveTelegramTarget(value);


    if (!resolved) {

        resolvedTargetChannel = null;

        renderTargetChannelResult();

        showToast(
            "Telegram kanal formatini tekshiring"
        );

        return;
    }


    resolvedTargetChannel =
        resolved;

    renderTargetChannelResult();

    haptic("light");
}


targetChannelInput.addEventListener(
    "blur",
    resolveTargetChannel
);


targetChannelInput.addEventListener(
    "change",
    resolveTargetChannel
);


/* =========================================
   REQUIRED CHANNELS
========================================= */

function renderRequiredChannels() {

    if (!requiredChannels.length) {

        requiredChannelList.innerHTML = "";

        return;
    }


    requiredChannelList.innerHTML =
        requiredChannels
            .map((channel, index) => {

                return `

                    <div class="channel-chip">

                        <div class="channel-chip-icon">
                            ${iconSvg("channel")}
                        </div>

                        <div class="channel-chip-info">

                            <strong>
                                ${escapeHtml(
                                    channel.title
                                )}
                            </strong>

                            <span>
                                ${escapeHtml(
                                    channel.username
                                )}
                            </span>

                        </div>

                        <button
                            type="button"
                            class="channel-remove"
                            data-remove-channel="${index}"
                            aria-label="O'chirish"
                        >
                            ${iconSvg("close")}
                        </button>

                    </div>

                `;

            })
            .join("");


    requiredChannelList
        .querySelectorAll(
            "[data-remove-channel]"
        )
        .forEach((button) => {

            button.addEventListener(
                "click",
                () => {

                    const index =
                        Number(
                            button.dataset
                                .removeChannel
                        );

                    requiredChannels.splice(
                        index,
                        1
                    );

                    renderRequiredChannels();

                    haptic("light");

                }
            );

        });
}


function addRequiredChannel() {

    const value =
        requiredChannelInput.value.trim();

    if (!value) {

        showToast(
            "Kanal username yoki ID kiriting"
        );

        return;
    }


    const resolved =
        resolveTelegramTarget(value);


    if (!resolved) {

        showToast(
            "Telegram kanal formatini tekshiring"
        );

        return;
    }


    const exists =
        requiredChannels.some(
            (channel) =>
                channel.key === resolved.key
        );


    if (exists) {

        showToast(
            "Bu kanal allaqachon qo'shilgan"
        );

        return;
    }


    requiredChannels.push(
        resolved
    );


    requiredChannelInput.value = "";

    renderRequiredChannels();

    haptic("medium");
}


addRequiredChannelButton.addEventListener(
    "click",
    addRequiredChannel
);


requiredChannelInput.addEventListener(
    "keydown",
    (event) => {

        if (event.key === "Enter") {

            event.preventDefault();

            addRequiredChannel();

        }

    }
);


/* =========================================
   IMAGE
========================================= */

postImageInput.addEventListener(
    "change",
    (event) => {

        const file =
            event.target.files?.[0];

        if (!file) {
            return;
        }


        if (
            !file.type.startsWith(
                "image/"
            )
        ) {

            showToast(
                "Faqat rasm fayl tanlang"
            );

            postImageInput.value = "";

            return;
        }


        const reader =
            new FileReader();


        reader.onload = () => {

            selectedImageData =
                reader.result;

            postImagePreview.src =
                selectedImageData;

            imagePreviewBox.classList.remove(
                "hidden"
            );

            haptic("medium");

        };


        reader.readAsDataURL(file);
    }
);


removeImageButton.addEventListener(
    "click",
    () => {

        selectedImageData = "";

        postImageInput.value = "";

        postImagePreview.src = "";

        imagePreviewBox.classList.add(
            "hidden"
        );

        haptic("light");

    }
);


/* =========================================
   END TYPE
========================================= */

function setEndType(type) {

    currentEndType =
        type;


    const isTime =
        type === "time";


    endTypeTime.classList.toggle(
        "active",
        isTime
    );

    endTypeLimit.classList.toggle(
        "active",
        !isTime
    );


    endTimeField.classList.toggle(
        "hidden",
        !isTime
    );

    participantLimitField.classList.toggle(
        "hidden",
        isTime
    );

    haptic("light");
}


endTypeTime.addEventListener(
    "click",
    () => setEndType("time")
);


endTypeLimit.addEventListener(
    "click",
    () => setEndType("limit")
);


/* =========================================
   START MODE
========================================= */

function setStartMode(mode) {

    currentStartMode =
        mode;


    const isNow =
        mode === "now";


    startNowButton.classList.toggle(
        "active",
        isNow
    );

    startScheduledButton.classList.toggle(
        "active",
        !isNow
    );


    startTimeField.classList.toggle(
        "hidden",
        isNow
    );


    haptic("light");
}


startNowButton.addEventListener(
    "click",
    () => setStartMode("now")
);


startScheduledButton.addEventListener(
    "click",
    () => setStartMode("scheduled")
);


/* =========================================
   DATETIME HELPERS
========================================= */

function padNumber(number) {

    return String(number)
        .padStart(2, "0");
}


function toLocalDateTimeInput(
    date
) {

    const year =
        date.getFullYear();

    const month =
        padNumber(
            date.getMonth() + 1
        );

    const day =
        padNumber(
            date.getDate()
        );

    const hours =
        padNumber(
            date.getHours()
        );

    const minutes =
        padNumber(
            date.getMinutes()
        );


    return `${year}-${month}-${day}T${hours}:${minutes}`;
}


function setDateDefaults() {

    const now =
        new Date();


    const startDefault =
        new Date(
            now.getTime() +
            30 * 60 * 1000
        );


    const endDefault =
        new Date(
            now.getTime() +
            24 * 60 * 60 * 1000
        );


    const minimum =
        toLocalDateTimeInput(
            now
        );


    startAt.min =
        minimum;

    endAt.min =
        minimum;


    if (!startAt.value) {

        startAt.value =
            toLocalDateTimeInput(
                startDefault
            );

    }


    if (!endAt.value) {

        endAt.value =
            toLocalDateTimeInput(
                endDefault
            );

    }
}


/* =========================================
   DATE FORMAT
========================================= */

function formatDateTime(
    value
) {

    if (!value) {
        return "-";
    }


    const date =
        new Date(value);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return value;
    }


    return new Intl.DateTimeFormat(
        "uz-UZ",
        {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        }
    ).format(date);
}


/* =========================================
   VALIDATION
========================================= */

function validateContestForm() {

    resolveTargetChannel();


    if (!resolvedTargetChannel) {

        showToast(
            "Konkurs kanalini kiriting"
        );

        targetChannelInput.focus();

        return false;
    }


    if (
        !postText.value.trim() &&
        !selectedImageData
    ) {

        showToast(
            "Postga matn yoki rasm qo'shing"
        );

        postText.focus();

        return false;
    }


    if (!requiredChannels.length) {

        showToast(
            "Kamida 1 ta majburiy kanal qo'shing"
        );

        requiredChannelInput.focus();

        return false;
    }


    const winners =
        Number(
            winnersCount.value
        );


    if (
        !Number.isInteger(winners) ||
        winners < 1
    ) {

        showToast(
            "G'oliblar sonini to'g'ri kiriting"
        );

        winnersCount.focus();

        return false;
    }


    if (
        !buttonText.value.trim()
    ) {

        showToast(
            "Ishtirok etish tugmasi matnini kiriting"
        );

        buttonText.focus();

        return false;
    }


    if (
        currentEndType === "time"
    ) {

        if (!endAt.value) {

            showToast(
                "Tugash vaqtini tanlang"
            );

            endAt.focus();

            return false;
        }


        const endDate =
            new Date(
                endAt.value
            );


        const now =
            new Date();


        if (
            endDate <= now
        ) {

            showToast(
                "Tugash vaqti kelajakda bo'lishi kerak"
            );

            endAt.focus();

            return false;
        }

    } else {

        const limit =
            Number(
                participantLimit.value
            );


        if (
            !Number.isInteger(limit) ||
            limit < 1
        ) {

            showToast(
                "Ishtirokchilar limitini kiriting"
            );

            participantLimit.focus();

            return false;
        }


        if (limit < winners) {

            showToast(
                "Ishtirokchilar soni g'oliblardan kam bo'lmasin"
            );

            participantLimit.focus();

            return false;
        }

    }


    if (
        currentStartMode === "scheduled"
    ) {

        if (!startAt.value) {

            showToast(
                "Boshlanish vaqtini tanlang"
            );

            startAt.focus();

            return false;
        }


        const startDate =
            new Date(
                startAt.value
            );


        const now =
            new Date();


        if (
            startDate <= now
        ) {

            showToast(
                "Boshlanish vaqti kelajakda bo'lishi kerak"
            );

            startAt.focus();

            return false;
        }


        if (
            currentEndType === "time" &&
            endAt.value
        ) {

            const endDate =
                new Date(
                    endAt.value
                );


            if (
                startDate >= endDate
            ) {

                showToast(
                    "Boshlanish vaqti tugash vaqtidan oldin bo'lishi kerak"
                );

                startAt.focus();

                return false;
            }

        }

    }


    return true;
}


/* =========================================
   BUILD DATA
========================================= */

function buildContestData() {

    const startDate =
        currentStartMode === "now"
            ? new Date()
            : new Date(
                startAt.value
            );


    const data = {

        id:
            Date.now(),

        targetChannel:
            {
                ...resolvedTargetChannel
            },

        postText:
            postText.value.trim(),

        image:
            selectedImageData,

        requiredChannels:
            requiredChannels.map(
                (channel) => ({
                    ...channel
                })
            ),

        endType:
            currentEndType,

        endAt:
            currentEndType === "time"
                ? endAt.value
                : null,

        participantLimit:
            currentEndType === "limit"
                ? Number(
                    participantLimit.value
                )
                : null,

        winnersCount:
            Number(
                winnersCount.value
            ),

        buttonText:
            buttonText.value.trim(),

        startMode:
            currentStartMode,

        startAt:
            startDate.toISOString(),

        participants:
            0,

        status:
            currentStartMode === "now"
                ? "Faol"
                : "Rejalashtirilgan",

        createdAt:
            new Date().toISOString(),

    };


    return data;
}


/* =========================================
   PREVIEW
========================================= */

function renderPreview(data) {

    previewContestData =
        data;


    const imageHtml =
        data.image
            ? `
                <img
                    class="preview-post-image"
                    src="${data.image}"
                    alt="Konkurs rasmi"
                >
            `
            : "";


    const postTextHtml =
        data.postText
            ? `
                <div class="preview-post-text">
                    ${escapeHtml(
                        data.postText
                    )}
                </div>
            `
            : `
                <div class="preview-post-text">
                    Konkurs posti
                </div>
            `;


    const startText =
        data.startMode === "now"
            ? "Hozir"
            : formatDateTime(
                data.startAt
            );


    const endText =
        data.endType === "time"
            ? formatDateTime(
                data.endAt
            )
            : `${data.participantLimit} ta ishtirokchi`;


    const requiredChannelsHtml =
        data.requiredChannels
            .map(
                (channel) => `
                    <span class="preview-channel-chip">
                        ${escapeHtml(
                            channel.username
                        )}
                    </span>
                `
            )
            .join("");


    previewContent.innerHTML = `

        <!-- TELEGRAM POST MOCK -->

        <div class="preview-post">

            ${imageHtml}

            <div class="preview-post-body">

                <div class="preview-post-channel">

                    <div class="preview-channel-avatar">
                        K
                    </div>

                    <div>
                        <strong>
                            ${escapeHtml(
                                data.targetChannel.title
                            )}
                        </strong>

                        <span>
                            Konkurs kanali
                        </span>
                    </div>

                </div>


                ${postTextHtml}


                <button
                    type="button"
                    class="preview-post-button"
                >
                    ${escapeHtml(
                        data.buttonText
                    )}
                </button>

            </div>

        </div>


        <!-- DETAILS -->

        <div class="preview-info-grid">

            <div class="preview-info">

                <span>
                    BOSHLANISHI
                </span>

                <strong>
                    ${escapeHtml(
                        startText
                    )}
                </strong>

            </div>


            <div class="preview-info">

                <span>
                    TUGASHI
                </span>

                <strong>
                    ${escapeHtml(
                        endText
                    )}
                </strong>

            </div>


            <div class="preview-info">

                <span>
                    G'OLIBLAR
                </span>

                <strong>
                    ${data.winnersCount} ta
                </strong>

            </div>


            <div class="preview-info">

                <span>
                    ISHTIROKCHILAR
                </span>

                <strong>
                    0
                </strong>

            </div>

        </div>


        <div class="preview-section">

            <div class="preview-section-title">
                Konkurs kanali
            </div>

            <div class="preview-channel-row">

                <span class="preview-channel-chip">
                    ${escapeHtml(
                        data.targetChannel.username
                    )}
                </span>

            </div>

        </div>


        <div class="preview-section">

            <div class="preview-section-title">
                Majburiy kanallar
            </div>

            <div class="preview-channel-row">

                ${requiredChannelsHtml}

            </div>

        </div>

    `;


    previewModal.classList.remove(
        "hidden"
    );


    document.body.style.overflow =
        "hidden";


    haptic("medium");
}


/* =========================================
   PREVIEW FORM SUBMIT
========================================= */

contestForm.addEventListener(
    "submit",
    (event) => {

        event.preventDefault();


        if (
            !validateContestForm()
        ) {
            return;
        }


        const data =
            buildContestData();


        renderPreview(data);

    }
);


/* =========================================
   CLOSE PREVIEW
========================================= */

function closePreview() {

    previewModal.classList.add(
        "hidden"
    );

    document.body.style.overflow =
        "";

    haptic("light");
}


closePreviewButton.addEventListener(
    "click",
    closePreview
);


editPreviewButton.addEventListener(
    "click",
    closePreview
);


previewModal.addEventListener(
    "click",
    (event) => {

        if (
            event.target ===
            previewModal
        ) {

            closePreview();

        }

    }
);


/* =========================================
   LOCAL STORAGE
========================================= */

function loadContests() {

    try {

        const saved =
            localStorage.getItem(
                "konkurs_uzbot_contests"
            );


        if (!saved) {
            return [];
        }


        const parsed =
            JSON.parse(saved);


        if (
            !Array.isArray(parsed)
        ) {
            return [];
        }


        return parsed;

    } catch (error) {

        console.log(
            "Contest load error",
            error
        );

        return [];

    }
}


function saveContests() {

    try {

        localStorage.setItem(
            "konkurs_uzbot_contests",
            JSON.stringify(
                contests
            )
        );

    } catch (error) {

        console.log(
            "Contest save error",
            error
        );

    }
}


/* =========================================
   CONFIRM CONTEST
========================================= */

confirmContestButton.addEventListener(
    "click",
    () => {

        if (!previewContestData) {
            return;
        }


        contests.unshift(
            previewContestData
        );


        saveContests();


        closePreview();


        resetContestForm();


        showToast(
            previewContestData.startMode === "now"
                ? "Konkurs hozir boshlandi"
                : "Konkurs rejalashtirildi"
        );


        setTimeout(
            () => {
                showPage(
                    "my-contests"
                );
            },
            500
        );


        previewContestData = null;

    }
);


/* =========================================
   RESET FORM
========================================= */

function resetContestForm() {

    contestForm.reset();


    selectedImageData =
        "";

    resolvedTargetChannel =
        null;

    requiredChannels =
        [];


    currentEndType =
        "time";

    currentStartMode =
        "now";


    imagePreviewBox.classList.add(
        "hidden"
    );

    postImagePreview.src =
        "";

    postImageInput.value =
        "";


    targetChannelResult.classList.add(
        "hidden"
    );

    targetChannelResult.innerHTML =
        "";


    renderRequiredChannels();


    setEndType("time");

    setStartMode("now");

    setDateDefaults();


    winnersCount.value =
        "1";

    buttonText.value =
        "Ishtirok etish";
}


/* =========================================
   MY CONTESTS
========================================= */

function getContestStatus(
    contest
) {

    if (
        contest.status === "Faol"
    ) {

        return "Faol";
    }


    if (
        contest.status === "Yakunlangan"
    ) {

        return "Yakunlangan";
    }


    return "Rejalashtirilgan";
}


function renderMyContests() {

    if (!contests.length) {

        myContestsList.innerHTML =
            "";

        myContestsEmpty.classList.remove(
            "hidden"
        );

        return;
    }


    myContestsEmpty.classList.add(
        "hidden"
    );


    myContestsList.innerHTML =
        contests
            .map((contest) => {

                const status =
                    getContestStatus(
                        contest
                    );


                const endText =
                    contest.endType === "time"
                        ? formatDateTime(
                            contest.endAt
                        )
                        : `${contest.participantLimit} ta`;


                return `

                    <div class="contest-card">

                        <div class="contest-card-top">

                            <div class="contest-mini-icon">
                                ${iconSvg("trophy")}
                            </div>


                            <div class="contest-card-info">

                                <strong>
                                    ${escapeHtml(
                                        contest.targetChannel.title
                                    )}
                                </strong>

                                <span>
                                    ${escapeHtml(
                                        contest.buttonText
                                    )}
                                </span>

                            </div>


                            <div class="contest-status">
                                ${escapeHtml(
                                    status
                                )}
                            </div>

                        </div>


                        <div class="contest-card-details">

                            <div class="contest-detail">

                                <span>
                                    BOSHLANISHI
                                </span>

                                <strong>
                                    ${
                                        contest.startMode === "now"
                                            ? "Hozir"
                                            : escapeHtml(
                                                formatDateTime(
                                                    contest.startAt
                                                )
                                            )
                                    }
                                </strong>

                            </div>


                            <div class="contest-detail">

                                <span>
                                    TUGASHI
                                </span>

                                <strong>
                                    ${escapeHtml(
                                        endText
                                    )}
                                </strong>

                            </div>


                            <div class="contest-detail">

                                <span>
                                    G'OLIBLAR
                                </span>

                                <strong>
                                    ${contest.winnersCount} ta
                                </strong>

                            </div>


                            <div class="contest-detail">

                                <span>
                                    ISHTIROKCHILAR
                                </span>

                                <strong>
                                    ${contest.participants || 0}
                                </strong>

                            </div>

                        </div>

                    </div>

                `;

            })
            .join("");
}


/* =========================================
   HELP
========================================= */

const helpTexts = {

    create: `
        <strong>Konkurs yaratish</strong>
        <br><br>
        Konkurs kanalini kiriting
        keyin post matni va kerak bo'lsa
        gallerydan rasm tanlang.
        <br><br>
        Majburiy obuna kanallarini qo'shing
        va tugash shartini belgilang.
        <br><br>
        G'oliblar soni va ishtirok etish
        tugmasini sozlab preview orqali
        konkursni tasdiqlashingiz mumkin.
    `,

    participation: `
        <strong>Konkursda qatnashish</strong>
        <br><br>
        Kanal postidagi ishtirok etish
        tugmasini bosing.
        <br><br>
        Bot kerakli kanallarga obuna
        bo'lganingizni tekshiradi.
        Barcha shartlar bajarilgach
        konkursda qatnashasiz.
    `,

    winners: `
        <strong>G'oliblar</strong>
        <br><br>
        Konkurs yakunlangach bot
        ishtirokchilar orasidan tasodifiy
        g'oliblarni tanlaydi.
        <br><br>
        Bir foydalanuvchi bir konkursda
        faqat bir marta ishtirok eta oladi.
    `,

    faq: `
        <strong>FAQ</strong>
        <br><br>
        Konkursni hozir boshlash yoki
        kelajakdagi vaqtga rejalashtirish
        mumkin.
        <br><br>
        Tugash sharti vaqt yoki
        ishtirokchilar soni bo'lishi mumkin.
    `,

    admin: `
        <strong>Admin bilan bog'lanish</strong>
        <br><br>
        Muammo yoki savol bo'lsa
        bot administratori bilan
        Telegram orqali bog'lanishingiz mumkin.
    `,

};


document
    .querySelectorAll("[data-help]")
    .forEach((button) => {

        button.addEventListener(
            "click",
            () => {

                const type =
                    button.dataset.help;

                const text =
                    helpTexts[type];

                if (!text) {
                    return;
                }


                showHelpDetail(
                    text
                );

            }
        );

    });


function showHelpDetail(
    content
) {

    const page =
        pages.help;


    page.innerHTML = `

        <div class="page-header">

            <button
                class="back-icon-button"
                id="help-detail-back"
                type="button"
            >
                <svg viewBox="0 0 24 24">
                    <path d="m15 18-6-6 6-6"/>
                </svg>
            </button>

            <div class="page-header-icon">

                <svg viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="9"/>
                    <path d="M9.5 9a2.5 2.5 0 1 1 4.2 1.8c-.9.8-1.7 1.2-1.7 2.7"/>
                    <path d="M12 17h.01"/>
                </svg>

            </div>

            <div>
                <h2>Yordam</h2>
                <p>Ma'lumot</p>
            </div>

        </div>


        <div class="form-section">

            <div class="help-detail-content">
                ${content}
            </div>

        </div>

    `;


    document
        .getElementById(
            "help-detail-back"
        )
        .addEventListener(
            "click",
            () => {

                restoreHelpPage();

            }
        );

}


function restoreHelpPage() {

    location.reload();

}


/* =========================================
   INPUT EVENTS
========================================= */

startAt.addEventListener(
    "change",
    () => {

        const minimum =
            toLocalDateTimeInput(
                new Date()
            );

        startAt.min =
            minimum;

    }
);


endAt.addEventListener(
    "change",
    () => {

        const minimum =
            toLocalDateTimeInput(
                new Date()
            );

        endAt.min =
            minimum;

    }
);


/* =========================================
   INITIALIZE
========================================= */

function initializeApp() {

    loadProfile();

    setDateDefaults();

    setEndType("time");

    setStartMode("now");

    renderRequiredChannels();

    renderMyContests();

    showPage("home");

    if (tg) {

        try {
            tg.MainButton.hide();
        } catch (error) {
            console.log(error);
        }

    }

}


document.addEventListener(
    "DOMContentLoaded",
    initializeApp
);