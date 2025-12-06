/*
Local storage data structure.

TTL value

getItem key = "shopping-list-{date}-ttl"

{
    "last_viewed": "2025-01-01"
}

Selected shopping list items

getItem key = "shopping-list-{date}"

{
    "date": "2025-01-01",
    "selected_items": [
        "id": "some-uuid"
    ]
}
*/

const SHOPPING_LIST_TTL_KEY = 'shopping-list-ttls';
const SHOPPING_LIST_CHECKED_ITEMS_KEY = 'shopping-list-checked-items';
const LAST_VIEWED_KEY = 'last_viewed';
const SHOPPING_LIST_TTL_DAYS = 7;

function addDays(date, days) {
    console.log(`Adding ${days} to ${date}`);
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    console.log(result)
    return result;
}

async function pruneExpiredShoppingLists() {
    console.log(`Pruning lists older than ${SHOPPING_LIST_TTL_DAYS} days.`);

    var ttlData = JSON.parse(localStorage.getItem(SHOPPING_LIST_TTL_KEY));
    var checkedData = JSON.parse(localStorage.getItem(SHOPPING_LIST_CHECKED_ITEMS_KEY) || '{}');

    for (const listID in ttlData) {
        console.log(`Checking age of ${listID}`);
        const lastViewed = ttlData[listID][LAST_VIEWED_KEY];
        if (new Date() >= addDays(new Date(lastViewed), SHOPPING_LIST_TTL_DAYS)) {
            console.log('Expired, evicting.');

            // Delete TTL data
            delete ttlData[listID];

            // Delete checked list data
            var curentListCheckedData = checkedData[listID] || {};
            delete curentListCheckedData[listItemID];
        }
    }

    localStorage.setItem(SHOPPING_LIST_TTL_KEY, JSON.stringify(ttlData));
    localStorage.setItem(SHOPPING_LIST_CHECKED_ITEMS_KEY, JSON.stringify(checkedData));
}

async function setCheckboxesFromLocalStorage() {
    console.log('Setting checkboxes from localStorage');

    const listID = document.getElementById('listID').innerHTML;
    var checkedData = JSON.parse(localStorage.getItem(SHOPPING_LIST_CHECKED_ITEMS_KEY) || '{}');

    var curentListCheckedData = checkedData[listID] || {};

    document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        if (curentListCheckedData.hasOwnProperty(checkbox.value)) {
            checkbox.checked = 'true';
        }
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    // Get the date of the current list
    const listID = document.getElementById('listID').innerHTML;
    console.log(`Current list date ${listID}`);

    var ttlData = JSON.parse(localStorage.getItem(SHOPPING_LIST_TTL_KEY) || '{}');
    console.log('Existing TTL data');
    console.log(ttlData);

    const today = new Date();
    const storableDate = `${today.getFullYear()}-${today.getMonth() + 1}-${today.getDate()}`;

    var currentListTTLData = ttlData[listID] || {};

    currentListTTLData[LAST_VIEWED_KEY] = storableDate;

    ttlData[listID] = currentListTTLData;

    localStorage.setItem(SHOPPING_LIST_TTL_KEY, JSON.stringify(ttlData));

    console.log('Updated TTL data');
    console.log(ttlData)

    // Dispatch a promise to set the selected elements from localStorage for the current list
    try {
        await setCheckboxesFromLocalStorage();
    } catch (e) {
        console.error('Setting checkboxes from localStorage failed');
        console.error(e);
    }

    // Async prune expired shopping lists in localStorage
    try {
        await pruneExpiredShoppingLists();
    } catch (e) {
        console.error('Pruning failed');
        console.error(e);
    }
});

// Add an event listener to update localStorage with the newly-selected list item
document.addEventListener('change', (e) => {
    if (e.target === null) {
        return;
    }

    if (!e.target.matches('input[type="checkbox"]')) {
        return;
    }

    const listItemID = e.target.value;
    const checked = e.target.checked;

    console.log(`Checkbox "${listItemID}" changed to ${checked}`);

    const listID = document.getElementById('listID').innerHTML;

    var checkedData = JSON.parse(localStorage.getItem(SHOPPING_LIST_CHECKED_ITEMS_KEY) || '{}');
    var curentListCheckedData = checkedData[listID] || {};

    if (checked) {
        console.log('Setting checked')
        curentListCheckedData[listItemID] = checked;
    } else {
        console.log('Deleting checked')
        delete curentListCheckedData[listItemID];
    }

    checkedData[listID] = curentListCheckedData;
    localStorage.setItem(SHOPPING_LIST_CHECKED_ITEMS_KEY, JSON.stringify(checkedData));
});
