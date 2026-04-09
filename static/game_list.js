let list = document.getElementById("list");
class Room {
    constructor(id, count_plaer, status){
        this.id = id;
        this.count_plaer = count_plaer;
        this.status = status;
    }
    CreateRoom(){

    }
    CreateList(list){
        let li = document.createElement('li');
        let div = document.createElement('div');
        let span = document.createElement('span');

        div.appendChild(span);
        li.appendChild(div);
        list.appendChild(li);
    }
    
}
const room1 = new Room()
room1.CreateList(list)