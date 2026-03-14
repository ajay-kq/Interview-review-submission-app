function rate(skill,value){

document.getElementById(skill+"_rating").value=value

let score=value*2

document.getElementById(skill+"_score").innerText=score+"/10"

}