import axios from "axios"

export const executeCode = async (code, problem, game_id, score) => {
    const payload = {
        "game_id": game_id,
        "code": code,
        "question_id": problem.id,
        "score": score
    }

    const result = await axios.post("http://locahost:8000/game/submit", payload,
        { withCredentials: true });
    
    console.log(result.data);

    return result.data;
}